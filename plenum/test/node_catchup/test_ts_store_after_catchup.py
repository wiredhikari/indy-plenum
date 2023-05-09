from common.serializers.serialization import domain_state_serializer, config_state_serializer
from plenum.common.constants import CONFIG_LEDGER_ID, GET_TXN_AUTHOR_AGREEMENT
from plenum.common.txn_util import get_req_id, get_from, get_txn_time, get_payload_data
from plenum.common.util import get_utc_epoch
from plenum.server.request_handlers.static_taa_helper import StaticTAAHelper
from plenum.test.buy_handler import BuyHandler
from plenum.test.constants import GET_BUY
from plenum.test.helper import sdk_send_random_and_check
from plenum.test.node_catchup.helper import waitNodeDataEquality
from plenum.test.pool_transactions.helper import disconnect_node_and_ensure_disconnected
from plenum.test.test_node import checkNodesConnected
from plenum.test.txn_author_agreement.conftest import set_txn_author_agreement_aml, taa_aml_request_module, aml_request_kwargs
from plenum.test.txn_author_agreement.helper import sdk_send_txn_author_agreement, gen_random_txn_author_agreement
from plenum.test.view_change.helper import start_stopped_node


def test_fill_ts_store_after_catchup(txnPoolNodeSet,
                                     looper,
                                     sdk_pool_handle,
                                     sdk_wallet_steward,
                                     tconf,
                                     tdir,
                                     allPluginsPath
                                     ):
    sdk_send_random_and_check(looper, txnPoolNodeSet,
                              sdk_pool_handle, sdk_wallet_steward, 5)
    node_to_disconnect = txnPoolNodeSet[-1]

    disconnect_node_and_ensure_disconnected(looper,
                                            txnPoolNodeSet,
                                            node_to_disconnect)
    looper.removeProdable(name=node_to_disconnect.name)
    sdk_replies = sdk_send_random_and_check(looper, txnPoolNodeSet,
                                            sdk_pool_handle, sdk_wallet_steward, 2)

    node_to_disconnect = start_stopped_node(node_to_disconnect, looper, tconf,
                                            tdir, allPluginsPath)
    txnPoolNodeSet[-1] = node_to_disconnect
    looper.run(checkNodesConnected(txnPoolNodeSet))

    waitNodeDataEquality(looper, node_to_disconnect, *txnPoolNodeSet,
                         exclude_from_check=['check_last_ordered_3pc_backup'])
    req_handler = node_to_disconnect.read_manager.request_handlers[GET_BUY]
    for reply in sdk_replies:
        key = BuyHandler.prepare_buy_key(get_from(reply[1]['result']),
                                           get_req_id(reply[1]['result']))
        root_hash = req_handler.database_manager.ts_store.get_equal_or_prev(get_txn_time(reply[1]['result']))
        assert root_hash
        from_state = req_handler.state.get_for_root_hash(root_hash=root_hash,
                                                         key=key)
        assert domain_state_serializer.deserialize(from_state)['amount'] == \
               get_payload_data(reply[1]['result'])['amount']


def create_random_taa():
    text, version = gen_random_txn_author_agreement()
    return version, text


def test_fill_ts_store_for_config_after_catchup(txnPoolNodeSet,
                                                looper,
                                                sdk_pool_handle,
                                                sdk_wallet_trustee,
                                                tconf,
                                                tdir,
                                                allPluginsPath,
                                                set_txn_author_agreement_aml):
    sdk_send_txn_author_agreement(looper, sdk_pool_handle, sdk_wallet_trustee, *create_random_taa(),
                                  ratified=get_utc_epoch() - 600)
    node_to_disconnect = txnPoolNodeSet[-1]

    disconnect_node_and_ensure_disconnected(looper,
                                            txnPoolNodeSet,
                                            node_to_disconnect)
    looper.removeProdable(name=node_to_disconnect.name)
    sdk_reply = sdk_send_txn_author_agreement(looper, sdk_pool_handle, sdk_wallet_trustee, *create_random_taa(),
                                              ratified=get_utc_epoch() - 600)

    node_to_disconnect = start_stopped_node(node_to_disconnect, looper, tconf,
                                            tdir, allPluginsPath)
    txnPoolNodeSet[-1] = node_to_disconnect
    looper.run(checkNodesConnected(txnPoolNodeSet))

    waitNodeDataEquality(looper, node_to_disconnect, *txnPoolNodeSet,
                         exclude_from_check=['check_last_ordered_3pc_backup'])
    req_handler = node_to_disconnect.read_manager.request_handlers[GET_TXN_AUTHOR_AGREEMENT]
    last_digest = StaticTAAHelper.get_taa_digest(req_handler.state)
    key = StaticTAAHelper.state_path_taa_digest(last_digest)
    root_hash = req_handler.database_manager.ts_store.get_equal_or_prev(get_txn_time(sdk_reply[1]['result']), ledger_id=CONFIG_LEDGER_ID)
    assert root_hash
    from_state = req_handler.state.get_for_root_hash(root_hash=root_hash,
                                                     key=key)
    assert config_state_serializer.deserialize(from_state)['val']['text'] == \
           get_payload_data(sdk_reply[1]['result'])['text']
