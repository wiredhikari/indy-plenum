import libnacl.sign

from typing import Optional
import json

from plenum.common.constants import DATA
from plenum.common.request import Request
from common.serializers.serialization import domain_state_serializer
from plenum.common.exceptions import InvalidClientRequest, MissingSignature, InvalidSignature

from plenum.server.database_manager import DatabaseManager
from common.serializers.json_serializer import JsonSerializer
from plenum.common.types import f
from plenum.server.plugin.did_plugin import DID_PLUGIN_LEDGER_ID
from plenum.server.plugin.did_plugin.constants import  UPDATE_NETWORK_DID
from plenum.server.request_handlers.handler_interfaces.read_request_handler import ReadRequestHandler
# from plenum.server.plugin.did_plugin.request_handlers.create_security_domain_did import CreateSDDIDHandler
from plenum.server.plugin.did_plugin.request_handlers.create_security_domain_did import CreateSDDIDRequest
from plenum.server.plugin.did_plugin.request_handlers.abstract_did_req_handler import AbstractDIDReqHandler
from plenum.server.plugin.did_plugin.common import DID, NetworkDID, UPDATE_DID, did_id_from_url, libnacl_validate, libnacl_validate2


from plenum.common.txn_util import get_payload_data, get_from, \
    get_seq_no, get_txn_time, get_request_data

import libnacl
import libnacl.encode

class UpdateNetworkDIDHandler(ReadRequestHandler):
    did: NetworkDID = None
    did_str = None
    signatures = None
    this_indy_state = None

    # FETCH_DID type `__init__`
    # def __init__(self, database_manager: DatabaseManager):
    #     super().__init__(database_manager, UPDATE_NETWORK_DID, DID_PLUGIN_LEDGER_ID)

    def __init__(self, request_dict: str, indy_state) -> None:
        self.did_str = json.dumps(request_dict["DIDDocument"])
        self.did = NetworkDID(self.did_str)
        self.signatures = request_dict["signatures"]
        self.this_indy_state = indy_state

    def static_validation(self, request: Request):
        pass

    def get_list_of_dids(self, request: Request):
        did = request.operation.get(DATA).get("id").encode()
        return did
        # serialized_did = self.state.get(did, isCommitted=True)
        # did_data, proof = self._get_value_from_state(did, with_proof=True)
        
        # did = JsonSerializer().deserialize(serialized_did) if serialized_did else None

        # return {**request.operation, **{
        #     f.IDENTIFIER.nm: request.identifier,
        #     f.REQ_ID.nm: request.reqId,
        #     "did": did
        # }}
    
    def update_sddid(self, txn, request: Request):
        # Get All the DIDs present.
        dids = self.get_list_of_dids(request)

        # Fetch current UpdateDID_request @ID...
        current_did_id = "rANDOm"
        if current_did_id not in dids:
            # Call `create_security_domain_did.py` to create new SDDID.
            sd_did_json_string = self.did_str
            CreateSDDIDRequest(sd_did_json_string, self.state)
             
        # Update the SDDID_request ID.
        data = get_payload_data(txn).get(DATA)
        print("data.....::>", data)

        netwokMembers = []
        multisig_keys = []
        condition_or = []
        signature = {}
        sd_did_json = {
                          "SecurityDomainDIDDocument": {
                              "id": "did:iin_name:network_name",
                              "networkMembers": netwokMembers,
                              "verificationMethod": [
                                  {
                                      "id": "did:iin_name:network_name#multisig",
                                      "type": "BlockchainNetworkMultiSig",
                                      "controller": "did:iin_name:network_name",
                                      "multisigKeys": multisig_keys,
                                      "updatePolicy": {
                                          "id": "did:iin_name:network_name#updatepolicy",
                                          "controller": "did:iin_name:network_name",
                                          "type": "VerifiableCondition2021",
                                          "conditionAnd": [
                                              {
                                                  "id": "did:iin_name:network_name#updatepolicy-1",
                                                  "controller": "did:iin_name:network_name",
                                                  "type": "VerifiableCondition2021",
                                                  "conditionOr": condition_or
                                              },
                                              "did:iin_name:network_member_1#key1"
                                          ]
                                      }
                                  },
                                  {
                                      "id": "did:iin_name:network_name#fabriccerts",
                                      "type": "DataplaneCredentials",
                                      "controller": "did:iin_name:network_name",
                                      "FabricCredentials": {
                                          "did:iin_name:network_member_1": "Certificate3_Hash",
                                          "did:iin_name:network_member_2": "Certificate2_Hash",
                                          "did:iin_name:network_member_3": "Certificate3_Hash"
                                      }
                                  }
                              ],
                              "authentication": [
                                  "did:iin_name:network_name#multisig"
                              ],
                              "relayEndpoints": [
                                  {
                                      "hostname": "10.0.0.8",
                                      "port": "8888"
                                  },
                                  {
                                      "hostname": "10.0.0.9",
                                      "port": "8888"
                                  }
                              ]
                          },
                          "signatures": signature
                      }
        sd_did_json_string = json.dumps(sd_did_json)
        create_network_did_request = CreateSDDIDRequest(sd_did_json_string, self.state)

        self.did_dict[create_network_did_request.did.id] = create_network_did_request.did_str
        key = create_network_did_request.did.id
        val = self.did_dict[create_network_did_request.did.id]
        print("Setting state:", key, val)
        self.state.set(key.encode(), val)
        return val