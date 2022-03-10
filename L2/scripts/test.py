def run(nre):
    address, abi = nre.deploy("TradingFees", alias="tf")
    print(abi, address)

run()