// In setup spec, add the following block
/*methods {
    function PoolStatusManager.getAmountOut(PoolStatusManager.PoolStatus status, bool zeroForOne, uint256 amountIn) external returns (uint256,uint24,uint256) with (env e)
        => getAmountOutCVL(e.block.timestamp, status, zeroForOne, amountIn);

    function PoolStatusManager.getAmountIn(PoolStatusManager.PoolStatus status, bool zeroForOne, uint256 amountOut) external returns (uint256,uint24,uint256) with (env e)
        => getAmountInCVL(e.block.timestamp, status, zeroForOne, amountOut);
}*/

definition MAX_FEE_UNITS() returns uint24 = 10^6;
definition MAX_FEE_UNITS_MINUS_ONE() returns uint24 = 999999;

/// CVL implementation of _getReserves()
function getReservesByStatus(PoolStatusManager.PoolStatus status, bool zeroForOne) returns (uint256,uint256) {
    uint256 reserve0 = require_uint256(status.realReserve0 + status.mirrorReserve0);
    uint256 reserve1 = require_uint256(status.realReserve1 + status.mirrorReserve1);
    if(zeroForOne) {
        return (reserve0,reserve1);
    }
    return (reserve1,reserve0);
}

function validReservesAndAmounts(uint256 amount, uint256 reserveX, uint256 reserveY) returns bool {
    return amount > 0 && reserveX > 0 && reserveY > 0;
}

/// Summary for MarginFees.getAmountIn(address _poolManager, PoolStatus memory status, bool zeroForOne, uint256 amountOut)
function getAmountInCVL(uint256 timestamp, PoolStatusManager.PoolStatus status, bool zeroForOne, uint256 amountOut) 
returns (uint256,uint24,uint256) {
    uint256 reserveIn; uint256 reserveOut;
    reserveIn, reserveOut = getReservesByStatus(status, zeroForOne);
    require validReservesAndAmounts(amountOut, reserveOut, reserveIn);
    require amountOut < reserveOut;
    /* Deterministic approach (has limited dependency) */
    uint24 fee = dynamicFeeCVL(timestamp, status.marginTimestampLast, status.key.fee);
    uint256 amountInWithoutFee = amountInNoFeeCVL(amountOut, reserveOut, reserveIn);
    uint256 amountIn = attachedAmountInCVL(fee, amountInWithoutFee);
    uint256 feeAmount = assert_uint256(amountIn - amountInWithoutFee);
    return (amountIn, fee, feeAmount);
}

/// Summary for MarginFees.getAmountOut(PoolStatus memory status, bool zeroForOne, uint256 amountIn)
function getAmountOutCVL(uint256 timestamp, PoolStatusManager.PoolStatus status, bool zeroForOne, uint256 amountIn) 
returns (uint256,uint24,uint256) {
    uint256 reserveIn; uint256 reserveOut;
    reserveIn, reserveOut = getReservesByStatus(status, zeroForOne);
    require validReservesAndAmounts(amountIn, reserveOut, reserveIn);
    /* Deterministic approach (has limited dependency) */
    uint24 fee = dynamicFeeCVL(timestamp, status.marginTimestampLast, status.key.fee);
    uint256 feeAmount = feeAmountOutCVL(fee, amountIn);
    uint256 deducted = assert_uint256(amountIn - feeAmount);
    return (amountOutCVL(deducted, reserveOut, reserveIn), fee, feeAmount);
}

/// Ghost summary for MarginFees.dynamicFee(status) - assumes dependency on three parameters only.
ghost dynamicFeeCVL(uint256 /* timestamp */, uint256 /* last timestamp */, uint24 /* fee */) returns uint24 {
    axiom forall uint256 timestamp. forall uint256 lastTimestmap. forall uint24 fee.
        /// In an extreme case, the dynamic fee can actually be equal to MAX_FEE_UNITS(), but it will brick the function.
        /// We ignore this case for now as it isn't realistic.
        dynamicFeeCVL(timestamp,lastTimestmap,fee) < MAX_FEE_UNITS();
}

/// Ghost summary for amounts based on reserves and fees

/*
uint256 numerator = reserveIn * amountOut;
uint256 denominator = (reserveOut - amountOut);
uint256 amountInWithoutFee = (numerator / denominator) + 1;
*/
definition amountInNoFeeBound(uint256 amountInNoFee,uint256 amountOut,uint256 reserveOut,uint256 reserveIn) returns bool = 
    (amountInNoFee - 1) * (reserveOut - amountOut) <= reserveIn * amountOut
    &&
    (amountInNoFee - 1) * (reserveOut - amountOut) > (reserveIn + 1) * amountOut - reserveOut;

ghost amountInNoFeeCVL(uint256 /* amountOut */, uint256 /* reserveOut */, uint256 /* reserveIn */) returns uint256
{
    axiom forall uint256 amountOut. forall uint256 reserveOut. forall uint256 reserveIn.
        amountInNoFeeBound(amountInNoFeeCVL(amountOut,reserveOut,reserveIn),amountOut,reserveOut,reserveIn);
}

definition amountOutBound(uint256 amountOut,uint256 deducted,uint256 reserveOut,uint256 reserveIn) returns bool = 
    amountOut * (reserveIn + deducted) <= deducted * reserveOut
    &&
    amountOut * (reserveIn + deducted) >= deducted * (reserveOut - 1) - reserveIn;

ghost amountOutCVL(uint256 /* deducted */, uint256 /* reserveOut */, uint256 /* reserveIn */) returns uint256
{
    axiom forall uint256 deducted. forall uint256 reserveOut. forall uint256 reserveIn. 
        amountOutBound(amountOutCVL(deducted, reserveOut, reserveIn),deducted, reserveOut, reserveIn);
}

// ghost amountInNoFeeCVL(uint256 /* amountOut */, uint256 /* reserveOut */, uint256 /* reserveIn */) returns uint256;
// ghost amountOutCVL(uint256 /* deducted */, uint256 /* reserveOut */, uint256 /* reserveIn */) returns uint256 {
//     axiom forall uint256 deducted. forall uint256 reserveOut. forall uint256 reserveIn.
//         (reserveIn + deducted) * (reserveOut - amountOutCVL(deducted, reserveOut, reserveIn)) == reserveIn * reserveOut;
// }

ghost attachedAmountInCVL(uint24 /* fee */, uint256 /* amountInNoFees */) returns uint256 {
    axiom forall uint24 fee. forall uint256 amount.
        fee < MAX_FEE_UNITS() => attachedAmountInCVL(fee,amount) >= amount;

    axiom forall uint256 amount. attachedAmountInCVL(0, amount) == amount && 
        attachedAmountInCVL(MAX_FEE_UNITS_MINUS_ONE(), amount) == amount * MAX_FEE_UNITS();

    axiom forall uint256 amount. forall uint24 fee1. forall uint24 fee2.
        fee1 < fee2 && fee2 < MAX_FEE_UNITS() => attachedAmountInCVL(fee1, amount) <= attachedAmountInCVL(fee2, amount);
}

ghost feeAmountOutCVL(uint24 /* fee */, uint256 /* amountIn */) returns uint256 {
    axiom forall uint24 fee. forall uint256 amount.
        fee < MAX_FEE_UNITS() => feeAmountOutCVL(fee,amount) <= amount;

    axiom forall uint256 amount. feeAmountOutCVL(0, amount) == 0;

    axiom forall uint256 amount. forall uint24 fee1. forall uint24 fee2.
        fee1 < fee2 && fee2 < MAX_FEE_UNITS() => feeAmountOutCVL(fee1, amount) <= feeAmountOutCVL(fee2, amount);
}