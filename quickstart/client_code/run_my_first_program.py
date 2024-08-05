import asyncio
import os
from dotenv import load_dotenv
import py_nillion_client as nillion
from py_nillion_client import NodeKey, UserKey
from nillion_python_helpers import get_quote_and_pay, create_nillion_client, create_payments_config
from cosmpy.aerial.client import LedgerClient
from cosmpy.aerial.wallet import LocalWallet
from cosmpy.crypto.keypairs import PrivateKey

# Load environment variables
home = os.getenv("HOME")
load_dotenv(f"{home}/.config/nillion/nillion-devnet.env")

async def main():
    # 1. Initial setup
    cluster_id = os.getenv("NILLION_CLUSTER_ID")
    grpc_endpoint = os.getenv("NILLION_NILCHAIN_GRPC")
    chain_id = os.getenv("NILLION_NILCHAIN_CHAIN_ID")
    seed = "my_secure_seed"
    userkey = UserKey.from_seed(seed)
    nodekey = NodeKey.from_seed(seed)

    # 2. Initialize NillionClient
    client = create_nillion_client(userkey, nodekey)
    party_id = client.party_id
    user_id = client.user_id

    # 3. Store the program
    program_name = "main"
    program_mir_path = f"../nada_quickstart_programs/target/{program_name}.nada.bin"
    
    # Check if the program MIR file exists
    if not os.path.exists(program_mir_path):
        raise FileNotFoundError(f"The MIR file at path {program_mir_path} does not exist.")
    
    # Check file permissions
    if not os.access(program_mir_path, os.R_OK):
        raise PermissionError(f"The MIR file at path {program_mir_path} cannot be read. Check file permissions.")
    
    payments_config = create_payments_config(chain_id, grpc_endpoint)
    payments_client = LedgerClient(payments_config)
    payments_wallet = LocalWallet(
        PrivateKey(bytes.fromhex(os.getenv("NILLION_NILCHAIN_PRIVATE_KEY_0"))),
        prefix="nillion",
    )

    receipt_store_program = await get_quote_and_pay(
        client,
        nillion.Operation.store_program(program_mir_path),
        payments_wallet,
        payments_client,
        cluster_id,
    )

    action_id = await client.store_program(
        cluster_id, program_name, program_mir_path, receipt_store_program
    )

    program_id = f"{user_id}/{program_name}"
    print(f"Stored program. action_id: {action_id}")
    print(f"Stored program_id: {program_id}")

    # 4. Store secrets for Company A and Company B
    secret_values = nillion.NadaValues(
        {
            "bid_company_a": nillion.SecretInteger(10),  # Input bid for Company A
            "bid_company_b": nillion.SecretInteger(15),  # Input bid for Company B
        }
    )

    permissions = nillion.Permissions.default_for_user(client.user_id)
    permissions.add_compute_permissions({client.user_id: {program_id}})

    receipt_store = await get_quote_and_pay(
        client,
        nillion.Operation.store_values(secret_values, ttl_days=5),
        payments_wallet,
        payments_client,
        cluster_id,
    )

    store_id = await client.store_values(
        cluster_id, secret_values, permissions, receipt_store
    )
    print(f"Stored secrets. store_id: {store_id}")

    # 5. Compute
    compute_bindings = nillion.ProgramBindings(program_id)
    compute_bindings.add_input_party("CompanyA", party_id)
    compute_bindings.add_input_party("CompanyB", party_id)
    compute_bindings.add_output_party("Auctioneer", party_id)

    # Pass an empty dictionary for additional inputs
    receipt_compute = await get_quote_and_pay(
        client,
        nillion.Operation.compute(program_id, nillion.NadaValues({})),
        payments_wallet,
        payments_client,
        cluster_id,
    )

    compute_id = await client.compute(
        cluster_id,
        compute_bindings,
        [store_id],
        nillion.NadaValues({}),
        receipt_compute,
    )

    # 6. Get computation result
    print(f"Computation sent to network. compute_id: {compute_id}")
    while True:
        compute_event = await client.next_compute_event()
        if isinstance(compute_event, nillion.ComputeFinishedEvent):
            print(f"Compute complete for compute_id {compute_event.uuid}")
            print(f"The result is {compute_event.result.value}")
            return compute_event.result.value

if __name__ == "__main__":
    asyncio.run(main())
