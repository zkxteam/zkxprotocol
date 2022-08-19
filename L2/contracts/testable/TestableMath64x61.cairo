%lang starknet

from contracts.libraries.Math64x61 import Math64x61

##############
# Assertions #
##############

@view
func test_assert_64x61 {range_check_ptr} (x : felt):
    Math64x61.assert_64x61(x)
    return ()
end

@view
func test_assert_positive_64x61 {range_check_ptr} (x : felt):
    Math64x61.assert_positive_64x61(x)
    return ()
end

##############
# Conversion #
##############

@view
func test_from_felt {range_check_ptr} (x : felt, decimals : felt) -> (res : felt):
    let (res) = Math64x61.from_felt(x, decimals)
    return (res)
end

@view
func test_to_felt {range_check_ptr} (x : felt, decimals : felt) -> (res : felt):
    let (res) = Math64x61.to_felt(x, decimals)
    return (res)
end

###################
# Math operations #
###################

@view
func test_add {range_check_ptr} (x : felt, y : felt) -> (res : felt):
    let (res) = Math64x61.add(x, y)
    return (res)
end

@view
func test_sub {range_check_ptr} (x : felt, y : felt) -> (res : felt):
    let (res) = Math64x61.sub(x, y)
    return (res)
end

@view
func test_mul {range_check_ptr} (x : felt, y : felt) -> (res : felt):
    let (res) = Math64x61.mul(x, y)
    return (res)
end

@view
func test_div {range_check_ptr} (x : felt, y : felt) -> (res : felt):
    let (res) = Math64x61.div(x, y)
    return (res)
end

@view
func test_pow_int {range_check_ptr} (x : felt, y : felt) -> (res : felt):
    let (res) = Math64x61.pow_int(x, y)
    return (res)
end

@view
func test_sqrt {range_check_ptr} (x : felt) -> (res : felt):
    let (res) = Math64x61.sqrt(x)
    return (res)
end

@view
func test_msb {range_check_ptr} (x : felt) -> (res : felt):
    let (res) = Math64x61.msb(x)
    return (res)
end

@view
func test_exp {range_check_ptr} (x : felt) -> (res : felt):
    let (res) = Math64x61.exp(x)
    return (res)
end

@view
func test_exp2 {range_check_ptr} (x : felt) -> (res : felt):
    let (res) = Math64x61.exp2(x)
    return (res)
end

@view
func test_log2 {range_check_ptr} (x : felt) -> (res : felt):
    let (res) = Math64x61.log2(x)
    return (res)
end

@view
func test_ln {range_check_ptr} (x : felt) -> (res : felt):
    let (res) = Math64x61.ln(x)
    return (res)
end
