import string

import pytest

from plenum.common.event_bus import InternalBus
from plenum.common.messages.node_messages import ViewChange, ViewChangeAck, NewView, Checkpoint
from plenum.server.consensus.view_change_service import ViewChangeService, view_change_digest
from plenum.test.consensus.helper import some_pool
from plenum.test.helper import MockNetwork


@pytest.fixture
def view_change_service(consensus_data, mock_timer):
    def _service(name):
        data = consensus_data(name)
        service = ViewChangeService(data, mock_timer, InternalBus(), MockNetwork())
        return service
    return _service


@pytest.fixture
def view_change_message():
    def _view_change(view_no: int):
        vc = ViewChange(
            viewNo=view_no,
            stableCheckpoint=4,
            prepared=[],
            preprepared=[],
            checkpoints=[Checkpoint(instId=0, viewNo=view_no, seqNoStart=0, seqNoEnd=4, digest='some')]
        )
        return vc
    return _view_change


@pytest.fixture
def view_change_acks(validators, random):
    def _view_change_acks(vc, vc_frm, primary, count):
        digest = view_change_digest(vc)
        non_senders = [name for name in validators if name not in [vc_frm, primary]]
        ack_frms = random.sample(non_senders, count)
        return [(ViewChangeAck(viewNo=vc.viewNo, name=vc_frm, digest=digest), ack_frm) for ack_frm in ack_frms]
    return _view_change_acks


def test_view_change_primary_selection(validators, initial_view_no):
    primary = ViewChangeService._find_primary(validators, initial_view_no)
    prev_primary = ViewChangeService._find_primary(validators, initial_view_no - 1)
    next_primary = ViewChangeService._find_primary(validators, initial_view_no + 1)

    assert primary in validators
    assert prev_primary in validators
    assert next_primary in validators

    assert primary != prev_primary
    assert primary != next_primary


def test_start_view_change_increases_next_view_changes_primary_and_broadcasts_view_change_message(
        some_item, validators, view_change_service, initial_view_no):
    service = view_change_service(some_item(validators))
    old_primary = service._data.primary_name

    service.start_view_change()

    assert service._data.view_no == initial_view_no + 1
    assert service._data.waiting_for_new_view
    assert service._data.primary_name != old_primary

    assert len(service._network.sent_messages) == 1

    msg, dst = service._network.sent_messages[0]
    assert dst is None  # message was broadcast
    assert isinstance(msg, ViewChange)
    assert msg.viewNo == initial_view_no + 1
    assert msg.stableCheckpoint == service._data.stable_checkpoint


def test_non_primary_responds_to_view_change_message_with_view_change_ack_to_new_primary(
        some_item, other_item, validators, primary, view_change_service, initial_view_no, view_change_message):
    next_view_no = initial_view_no + 1
    non_primary_name = some_item(validators, exclude=[primary(next_view_no)])
    service = view_change_service(non_primary_name)
    service.start_view_change()
    service._network.sent_messages.clear()

    vc = view_change_message(next_view_no)
    frm = other_item(validators, exclude=[non_primary_name])
    service._network.process_incoming(vc, frm)

    assert len(service._network.sent_messages) == 1
    msg, dst = service._network.sent_messages[0]
    assert dst == service._data.primary_name
    assert isinstance(msg, ViewChangeAck)
    assert msg.viewNo == vc.viewNo
    assert msg.name == frm
    assert msg.digest == view_change_digest(vc)


def test_primary_doesnt_respond_to_view_change_message(
        some_item, validators, primary, view_change_service, initial_view_no, view_change_message):
    name = primary(initial_view_no + 1)
    service = view_change_service(name)

    vc = view_change_message(initial_view_no + 1)
    frm = some_item(validators, exclude=[name])
    service._network.process_incoming(vc, frm)

    assert len(service._network.sent_messages) == 0


def test_new_view_message_is_sent_once_when_view_change_certificate_is_reached(
        validators, primary, view_change_service, initial_view_no, view_change_message, view_change_acks):
    primary_name = primary(initial_view_no + 1)
    service = view_change_service(primary_name)
    service.start_view_change()
    service._network.sent_messages.clear()

    non_primaries = [item for item in validators if item != primary_name]
    for vc_frm in non_primaries:
        vc = view_change_message(initial_view_no + 1)
        service._network.process_incoming(vc, vc_frm)

        for ack, ack_frm in view_change_acks(vc, vc_frm, primary_name, len(validators) - 2):
            service._network.process_incoming(ack, ack_frm)

    assert len(service._network.sent_messages) == 1
    msg, dst = service._network.sent_messages[0]
    assert dst is None  # message was broadcast
    assert isinstance(msg, NewView)
    assert msg.viewNo == initial_view_no + 1


def test_view_change_digest_is_256_bit_hexdigest(view_change_message, random):
    vc = view_change_message(random.integer(0, 10000))
    digest = view_change_digest(vc)
    assert isinstance(digest, str)
    assert len(digest) == 64
    assert all(v in string.hexdigits for v in digest)


def test_different_view_change_messages_have_different_digests(view_change_message, random):
    vc = view_change_message(random.integer(0, 10000))
    other_vc = view_change_message(random.integer(0, 10000))
    assert view_change_digest(vc) != view_change_digest(other_vc)


@pytest.mark.skip(reason='Now new view IS ambiguous, we need to understand why')
def test_new_view_is_unambiguous(random):
    # Create pool in some random initial state
    pool = some_pool(random)
    quorums = pool.nodes[0]._data.quorums

    # Get view change votes from all nodes
    view_change_messages = []
    for node in pool.nodes:
        network = MockNetwork()
        node._view_changer._network = network
        node._view_changer.start_view_change()
        view_change_messages.append(network.sent_messages[0][0])

    # Check that final batches to order are unambiguous
    cps = set()
    results = set()
    for _ in range(10):
        num_votes = quorums.strong.value
        votes = random.sample(view_change_messages, num_votes)
        # TODO: These functions depends only on quorums which are same across
        #  all pool, so it doesn't matter which nodes view change service
        #  we are using. Probably it makes sense to make this function static
        #  to make test more clear
        cp = pool.nodes[0]._view_changer._calc_checkpoint(votes)
        # All nodes in pool are honest, so we should always be able to decide
        # on stable checkpoint from n-f votes
        assert cp is not None
        batches = pool.nodes[0]._view_changer._calc_batches(cp, votes)
        results.add(tuple(batches))
    assert len(cps) == 1
    assert len(results) == 1
