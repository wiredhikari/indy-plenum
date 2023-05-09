from plenum.common.constants import CONFIG_LEDGER_ID
from plenum.common.messages.node_messages import Ordered
from plenum.test.helper import freshness, assertExp

from plenum.test.replica.conftest import *
from plenum.test.test_node import getPrimaryReplica
from stp_core.loop.eventually import eventually

FRESHNESS_TIMEOUT = 60
OLDEST_TS = 1499906903

LEDGER_IDS = [POOL_LEDGER_ID, CONFIG_LEDGER_ID, DOMAIN_LEDGER_ID]


@pytest.fixture(scope='function', params=[0])
def viewNo(tconf, request):
    return request.param


@pytest.fixture(scope="module")
def tconf(tconf):
    with freshness(tconf, enabled=True, timeout=FRESHNESS_TIMEOUT):
        yield tconf


@pytest.fixture(scope='function')
def mock_timestamp():
    return MockTimestamp(OLDEST_TS)


@pytest.fixture(scope='function')
def ledger_ids():
    return LEDGER_IDS


@pytest.fixture(scope='function', params=[0])
def inst_id(request):
    return request.param


@pytest.fixture(scope='function')
def replica_with_valid_requests(primary_replica):
    requests = {ledger_id: sdk_random_request_objects(1, identifier="did",
                                                      protocol_version=CURRENT_PROTOCOL_VERSION)[0]
                for ledger_id in LEDGER_IDS}

    def patched_consume_req_queue_for_pre_prepare(ledger_id, tm, view_no, pp_seq_no):
        reqs = [requests[ledger_id]] if len(primary_replica._ordering_service.requestQueues[ledger_id]) > 0 else []
        return [reqs, [], []]

    primary_replica._ordering_service._consume_req_queue_for_pre_prepare = patched_consume_req_queue_for_pre_prepare

    return primary_replica, requests


def set_current_time(replica, ts):
    replica.get_current_time.value = OLDEST_TS + ts
    replica.get_time_for_3pc_batch.value = int(OLDEST_TS + ts)


def check_and_pop_ordered_pre_prepare(replica, ledger_ids):
    ledgers_set = set(ledger_ids)
    while len(replica.outBox) > 0:
        msg = replica.outBox.popleft()
        ledgers_set.discard(msg.ledgerId)
        assert isinstance(msg, PrePrepare)
        assert len(msg.reqIdr) > 0
    assert not ledgers_set

    for ledger_id in ledger_ids:
        replica._ordering_service.requestQueues[ledger_id].clear()


def check_and_pop_freshness_pre_prepare(replica, ledger_ids):
    ledgers_set = set(ledger_ids)
    while len(replica.outBox) > 0:
        msg = replica.outBox.popleft()
        ledgers_set.discard(msg.ledgerId)
        assert isinstance(msg, PrePrepare)
        assert msg.reqIdr == tuple()
    assert not ledgers_set


def test_no_freshness_pre_prepare_when_disabled(tconf, primary_replica):
    with freshness(tconf, enabled=False, timeout=FRESHNESS_TIMEOUT):
        assert len(primary_replica.outBox) == 0

        primary_replica.send_3pc_batch()
        assert len(primary_replica.outBox) == 0

        set_current_time(primary_replica, FRESHNESS_TIMEOUT + 1)
        primary_replica.send_3pc_batch()
        assert len(primary_replica.outBox) == 0


def test_no_freshness_pre_prepare_for_non_master(tconf, primary_replica):
    primary_replica.isMaster = False
    primary_replica.instId = 1
    assert len(primary_replica.outBox) == 0

    primary_replica.send_3pc_batch()
    assert len(primary_replica.outBox) == 0

    set_current_time(primary_replica, FRESHNESS_TIMEOUT + 1)
    primary_replica.send_3pc_batch()
    assert len(primary_replica.outBox) == 0


def test_freshness_pre_prepare_initially(primary_replica):
    assert len(primary_replica.outBox) == 0
    primary_replica.send_3pc_batch()
    assert len(primary_replica.outBox) == 0


@pytest.mark.parametrize('ts', [
    0, 1, FRESHNESS_TIMEOUT, -1, -FRESHNESS_TIMEOUT
])
def test_freshness_pre_prepare_before_timeout(primary_replica, ts):
    assert len(primary_replica.outBox) == 0
    set_current_time(primary_replica, ts)
    primary_replica.send_3pc_batch()
    assert len(primary_replica.outBox) == 0


def test_freshness_pre_prepare_after_timeout(primary_replica):
    assert len(primary_replica.outBox) == 0
    primary_replica.send_3pc_batch()
    set_current_time(primary_replica, FRESHNESS_TIMEOUT + 1)
    primary_replica.send_3pc_batch()
    assert len(primary_replica.outBox) == 3

    check_and_pop_freshness_pre_prepare(primary_replica, [POOL_LEDGER_ID, DOMAIN_LEDGER_ID, CONFIG_LEDGER_ID])


def test_freshness_pre_prepare_not_resend_before_next_timeout(primary_replica):
    assert len(primary_replica.outBox) == 0

    set_current_time(primary_replica, FRESHNESS_TIMEOUT + 1)
    primary_replica.send_3pc_batch()
    assert len(primary_replica.outBox) == 3

    primary_replica.send_3pc_batch()
    assert len(primary_replica.outBox) == 3

    set_current_time(primary_replica, FRESHNESS_TIMEOUT + 1 + FRESHNESS_TIMEOUT)
    primary_replica.send_3pc_batch()
    assert len(primary_replica.outBox) == 3

    set_current_time(primary_replica, FRESHNESS_TIMEOUT + 1 + FRESHNESS_TIMEOUT + 1)
    primary_replica.send_3pc_batch()
    assert len(primary_replica.outBox) == 6


@pytest.mark.parametrize('ordered, refreshed', [
    ([POOL_LEDGER_ID], [DOMAIN_LEDGER_ID, CONFIG_LEDGER_ID]),
    ([DOMAIN_LEDGER_ID], [POOL_LEDGER_ID, CONFIG_LEDGER_ID]),
    ([CONFIG_LEDGER_ID], [POOL_LEDGER_ID, DOMAIN_LEDGER_ID]),
    ([POOL_LEDGER_ID, DOMAIN_LEDGER_ID], [CONFIG_LEDGER_ID]),
    ([POOL_LEDGER_ID, CONFIG_LEDGER_ID], [DOMAIN_LEDGER_ID]),
    ([DOMAIN_LEDGER_ID, CONFIG_LEDGER_ID], [POOL_LEDGER_ID]),
    ([POOL_LEDGER_ID, DOMAIN_LEDGER_ID, CONFIG_LEDGER_ID], [])
])
def test_freshness_pre_prepare_only_when_no_requests_for_ledger(tconf,
                                                                replica_with_valid_requests,
                                                                ordered, refreshed):
    replica, requests = replica_with_valid_requests
    for ordered_ledger_id in ordered:
        replica._ordering_service.requestQueues[ordered_ledger_id] = OrderedSet([requests[ordered_ledger_id].key])

    # send 3PC batch for requests
    assert len(replica.outBox) == 0
    set_current_time(replica, tconf.Max3PCBatchWait + 1)
    replica.send_3pc_batch()
    assert len(replica.outBox) == len(ordered)

    # wait for freshness timeout
    set_current_time(replica, FRESHNESS_TIMEOUT + 1)

    # order requests
    for i in range(len(ordered)):
        replica._ordering_service._order_3pc_key((0, i + 1))
    check_and_pop_ordered_pre_prepare(replica, ordered)

    # refresh state for unordered
    replica.send_3pc_batch()
    assert len(replica.outBox) == len(refreshed)
    check_and_pop_freshness_pre_prepare(replica, refreshed)


def test_order_empty_pre_prepare(looper, tconf, txnPoolNodeSet):
    assert all(node.master_replica.last_ordered_3pc == (0, 0) for node in txnPoolNodeSet)
    assert all(node.spylog.count(node.processOrdered) == 0 for node in txnPoolNodeSet)

    replica = getPrimaryReplica([txnPoolNodeSet[0]], instId=0)
    replica._ordering_service._do_send_3pc_batch(ledger_id=POOL_LEDGER_ID)

    looper.run(eventually(
        lambda: assertExp(
            all(
                node.master_replica.last_ordered_3pc == (0, 1) for node in txnPoolNodeSet
            )
        )
    ))
    looper.run(eventually(
        lambda: assertExp(
            all(
                node.spylog.count(node.processOrdered) == 1 for node in txnPoolNodeSet
            )
        )
    ))
