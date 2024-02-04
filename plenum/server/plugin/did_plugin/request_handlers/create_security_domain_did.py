import libnacl.sign

from typing import Optional
import json

from plenum.common.constants import DATA
from plenum.common.request import Request
from common.serializers.serialization import domain_state_serializer
from plenum.common.exceptions import InvalidClientRequest, MissingSignature, InvalidSignature

from plenum.server.database_manager import DatabaseManager
from plenum.server.plugin.did_plugin.constants import  SDDID
from plenum.server.plugin.did_plugin.request_handlers.abstract_did_req_handler import AbstractDIDReqHandler
from plenum.server.plugin.did_plugin.common import DID, NetworkDID, did_id_from_url, libnacl_validate


from plenum.common.txn_util import get_payload_data, get_from, \
    get_seq_no, get_txn_time, get_request_data

import libnacl
import libnacl.encode

"""
{
  "SecurityDomainDIDDocument": {
    "id": "did:<iin_name>:<network_name>",
    "networkMembers": [
      "did:<iin_name>:<network_member_1>",
      "did:<iin_name>:<network_member_2>",
      "did:<iin_name>:<network_member_3>"
    ],
    "verificationMethod": [{
        "id": "did:<iin_name>:<network_name>#multisig",
        "type": "BlockchainNetworkMultiSig",
        "controller": "did:<iin_name>:<network_name>",
        "multisigKeys": [
          "did:<iin_name>:<network_member_1>#key1",
          "did:<iin_name>:<network_member_2>#key3",
          "did:<iin_name>:<network_member_3>#key1"
        ],
        "updatePolicy": {
          "id": "did:<iin_name>:<network_name>#updatepolicy",
          "controller": "did:<iin_name>:<network_name>",
          "type": "VerifiableCondition2021",
          "conditionAnd": [{
              "id": "did:<iin_name>:<network_name>#updatepolicy-1",
              "controller": "did:<iin_name>:<network_name>",
              "type": "VerifiableCondition2021",
              "conditionOr": ["did:<iin_name>:<network_member_3>#key1",
                "did:<iin_name>:<network_member_2>#key3"
              ]
            },
            "did:<iin_name>:<network_member_1>#key1"
          ]
        }
      },

      {
        "id": "did:<iin_name>:<network_name>#fabriccerts",
        "type": "DataplaneCredentials",
        "controller": "did:<iin_name>:<network_name>",
        "FabricCredentials": {
          "did:<iin_name>:<network_member_1>": "Certificate3_Hash",
          "did:<iin_name>:<network_member_2>": "Certificate2_Hash",
          "did:<iin_name>:<network_member_3>": "Certificate3_Hash"
        }
      }
    ],
    "authentication": [
      "did:<iin_name>:<network_name>#multisig"
    ],
    "relayEndpoints": [{
        "hostname": "10.0.0.8",
        "port": "8888"
      },
      {
        "hostname": "10.0.0.9",
        "port": "8888"
      }

    ]
  },
  "signatures": {
    "did:<iin_name>:<network_member_1>": "...",
    "did:<iin_name>:<network_member_2>": "...",
    "did:<iin_name>:<network_member_3>": "..."
  }
}
"""

class CreateSDDIDRequest:
    did: NetworkDID = None
    did_str = None
    signatures = None
    this_indy_state = None
    print("hello1")
    def __init__(self, request_dict: str, indy_state) -> None:
        self.did_str = json.dumps(request_dict["DIDDocument"])
        print("hello2")
        self.did = NetworkDID(self.did_str)
        print("hello3")
        self.signatures = request_dict["signatures"]
        print("hello4")
        self.this_indy_state = indy_state
        print("hello5")
    def fetch_party_key_from_auth_method(self, party_did_id, auth_method):
        print("hello5.5")
        for candidate_key_url in auth_method["multisigKeys"]:
            print("hello6")
            base_url = did_id_from_url(candidate_key_url)
            print("hello6")
            if base_url == party_did_id:
                return candidate_key_url

    def fetch_party_verification_method(self, party_key_url):
        print("hello3")
        party_did_id = did_id_from_url(party_key_url)
        print("party_did_id                   ::>",party_did_id )
        # Fetch party did
        # TODO: if did is in some other iin network

        # 1 did:iin:someotheriin1:sdfsdfsd
        # did:iin:somethingelse:asdasd

        # If did is in the same indy iin network
        serialized_party_did = self.this_indy_state.get(party_did_id)
        # if not serialized_party_did:
            # raise "Could not resolve did " + party_did_id
        print(serialized_party_did)
        party_did = domain_state_serializer.deserialize(serialized_party_did)
        party_did = DID(party_did)
        party_authentication_method = party_did.fetch_authentication_method(party_key_url)
        return party_authentication_method

    def authenticate(self):
        # Get any one authentication method of type GroupMultiSig
        auth_method = self.did.fetch_authentication_method()
        print("AUTH_METHOD",auth_method["multisigKeys"])

        if not auth_method:
            raise MissingSignature("Authentication verification method not found in SDDIDDocument.")
        
        # Iterate of each participant
        for party_did_id in self.did.network_participants:
            # Fetch the key url from auth_method
            party_key_url = self.fetch_party_key_from_auth_method(party_did_id, auth_method)

            # Fetch verification key of the party
            party_verification_method = self.fetch_party_verification_method(party_key_url)

            # Validate signature of the party
            if party_verification_method["type"] == "libnacl":
                # validate signature
                # TODO: Json serialization is not faithful. Use ordered collections isntead.
                originalhash = libnacl.crypto_hash_sha256(self.did_str)
                libnacl_validate(party_verification_method["publicKeyBase64"], self.signatures[party_did_id], originalhash)

                # TODO: Add more authentication methods / some standard
            else:
                raise InvalidSignature("Unknown signature type: ", auth_method["type"])

        if auth_method["type"] == "libnacl":
            # validate signature
            self._libnacl_validate(auth_method["publicKeyBase64"], self.signature["sigbase64"])
            # TODO: Add more authentication methods / some standard
        else:
            raise InvalidSignature("Unknown signature type: ", auth_method["type"])

class CreateSDDIDHandler(AbstractDIDReqHandler):

    def __init__(self, database_manager: DatabaseManager, did_dict: dict):
        super().__init__(database_manager, SDDID, did_dict)

    def additional_dynamic_validation(self, request: Request, req_pp_time: Optional[int]):

        operation = request.operation
        create_network_did_request_dict = operation.get(DATA)
        
        # parse create did request
        # try:
        create_network_did_request = CreateSDDIDRequest(create_network_did_request_dict, self.state)
        # except:
            # raise InvalidClientRequest(request.identifier, request.reqId, "Malformed CREATE_NETWORK_DID request.")

        # TODO Check if the did uri corresponds to this iin or not.

        # Check if did already in this iin or not.
        serialized_did = self.state.get(create_network_did_request.did.id, isCommitted=True)
        if serialized_did:
            raise InvalidClientRequest(request.identifier, request.reqId, "DID already exists.")

        # Authenticate
        create_network_did_request.authenticate()


    def update_state(self, txn, prev_result, request, is_committed=False):
        data = get_payload_data(txn).get(DATA)
        create_network_did_request = CreateSDDIDRequest(data, self.state)

        self.did_dict[create_network_did_request.did.id] = create_network_did_request.did_str
        key = create_network_did_request.did.id
        val = self.did_dict[create_network_did_request.did.id]
        print("Setting state:", key, val)
        self.state.set(key.encode(), val)
        return val
