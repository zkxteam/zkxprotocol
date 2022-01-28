import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.testing.state import StarknetState
from starkware.starknet.compiler.compile import compile_starknet_files
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert

signer1 = Signer(123456789987654321)

@pytest.fixture
def global_var():
    pytest.user1 = None

@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def asset_factory():
    starknet = await Starknet.empty()
    state = await StarknetState.empty()
    contract_definition = compile_starknet_files(["contracts/Test.cairo"], debug_info=True)
    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer1.public_key, 0]
    )

    asset = await starknet.deploy(
        "contracts/Test.cairo",
        constructor_calldata=[]
    )

    # contract = StarknetContract(
    #     state=state, abi=contract_definition.abi, contract_address=asset.contract_address
    # )

    return asset, admin1

@pytest.mark.asyncio
async def test_asset(asset_factory):
    asset, admin1 = asset_factory

    execution_info = await signer1.send_transaction(admin1,asset.contract_address, 'addAsset', [ 2, str_to_felt("BTC"), str_to_felt("B"), str_to_felt("Y"), str_to_felt("ETH"), str_to_felt("E"), str_to_felt("Y") ])
    print(execution_info)

    execution_info = await asset.get_asset(1).call()
    print(execution_info.result)
    assert execution_info.result.asset.ticker == str_to_felt("BTC")

    execution_info = await asset.get_asset(0).call()
    print(execution_info.result)
    assert execution_info.result.asset.ticker == str_to_felt("ETH")