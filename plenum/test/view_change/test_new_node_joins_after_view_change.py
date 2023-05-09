import pytest

from plenum.test.pool_transactions.helper import \
    disconnect_node_and_ensure_disconnected

from plenum.test.node_catchup.helper import ensure_all_nodes_have_same_data
from plenum.test.spy_helpers import getAllReturnVals
from plenum.test.test_node import ensureElectionsDone, getNonPrimaryReplicas
from plenum.test.view_change.helper import ensure_view_change, start_stopped_node
from stp_core.loop.eventually import eventually

from plenum.test.helper import checkViewNoForNodes, sdk_send_random_and_check, waitForViewChange
from plenum.test.pool_transactions.conftest import sdk_node_theta_added_fixture
from plenum.test.primary_selection.conftest import sdk_one_node_added_fixture

from stp_core.common.log import getlogger

logger = getlogger()


@pytest.fixture(scope='module')
def new_node_in_correct_view(looper, txnPoolNodeSet,
                             sdk_one_node_added, sdk_pool_handle, sdk_wallet_client):
    for _ in range(5):
        sdk_send_random_and_check(looper, txnPoolNodeSet, sdk_pool_handle, sdk_wallet_client, 2)
    new_node = sdk_one_node_added
    looper.run(eventually(checkViewNoForNodes, txnPoolNodeSet, retryWait=1,
                          timeout=10))
    sdk_send_random_and_check(looper, txnPoolNodeSet, sdk_pool_handle,
                              sdk_wallet_client, 2)


def test_new_node_has_same_view_as_others(new_node_in_correct_view):
    """
    A node joins after view change.
    """


def test_old_non_primary_restart_after_view_change(new_node_in_correct_view,
                                                   looper, txnPoolNodeSet,
                                                   tdir,
                                                   allPluginsPath, tconf,
                                                   sdk_pool_handle,
                                                   sdk_wallet_client):
    """
    An existing non-primary node crashes and then view change happens,
    the crashed node comes back up after view change
    """
    node_to_stop = getNonPrimaryReplicas(txnPoolNodeSet, 0)[-1].node

    # Stop non-primary
    disconnect_node_and_ensure_disconnected(looper, txnPoolNodeSet,
                                            node_to_stop, stopNode=True)
    looper.removeProdable(node_to_stop)
    remaining_nodes = list(set(txnPoolNodeSet) - {node_to_stop})

    # Send some requests before view change
    sdk_send_random_and_check(looper, txnPoolNodeSet, sdk_pool_handle,
                              sdk_wallet_client, 5)
    old_view_no = txnPoolNodeSet[0].viewNo
    ensure_view_change(looper, remaining_nodes, custom_timeout=tconf.NEW_VIEW_TIMEOUT)
    waitForViewChange(looper, remaining_nodes, expectedViewNo=old_view_no + 1)
    ensureElectionsDone(looper, remaining_nodes)
    # Send some requests after view change
    sdk_send_random_and_check(looper, txnPoolNodeSet, sdk_pool_handle,
                              sdk_wallet_client, 5)

    restarted_node = start_stopped_node(node_to_stop, looper, tconf,
                                        tdir, allPluginsPath)
    txnPoolNodeSet = remaining_nodes + [restarted_node]
    looper.run(eventually(checkViewNoForNodes,
                          txnPoolNodeSet, old_view_no + 1, timeout=30))

    ensure_all_nodes_have_same_data(looper, nodes=txnPoolNodeSet)
    ensureElectionsDone(looper, txnPoolNodeSet)
