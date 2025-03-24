import "./MathSummary.spec";
import "./getAmountsSummary.spec";

using PoolStatusManager as Test;
using MarginFees as Fees;

methods {
    function Test.getAmountOut(PoolStatusManager.PoolStatus status, bool zeroForOne, uint256 amountIn) external returns (uint256,uint24,uint256);
    function Test.getAmountIn(PoolStatusManager.PoolStatus status, bool zeroForOne, uint256 amountOut) external returns (uint256,uint24,uint256);
    function Fees.dynamicFee(address,PoolStatusManager.PoolStatus) external returns (uint24);

    function _.marginOracleReader() external => PER_CALLEE_CONSTANT;
    function _.observeNow(address poolManager, PoolStatusManager.PoolStatus) external => observeNowCVL(calledContract, poolManager) expect (uint224,uint256);
}

/// All values of oracleReserve are identical for different PoolIds.
function observeNowCVL(address oracle, address PM) returns (uint224,uint256) {
    return (oracleReserves(oracle,PM),oraclePriceLast(oracle,PM));
}

function equalStatuses(PoolStatusManager.PoolStatus statusA, PoolStatusManager.PoolStatus statusB) returns bool {
    return statusA.realReserve0 == statusB.realReserve0 &&
        statusA.mirrorReserve0 == statusB.mirrorReserve0 &&
        statusA.realReserve1 == statusB.realReserve1 &&
        statusA.mirrorReserve1 == statusB.mirrorReserve1 &&
        statusA.marginTimestampLast == statusB.marginTimestampLast;
}

persistent ghost oracleReserves(address,address) returns uint224;
persistent ghost oraclePriceLast(address,address) returns uint256;

rule checkAxioms_dynamicFee(PoolStatusManager.PoolStatus statusA, PoolStatusManager.PoolStatus statusB) {
    env e;
    address poolManager;
    require equalStatuses(statusA, statusB);
    
    uint24 feeA = Fees.dynamicFee(e, poolManager, statusA);
    uint24 feeB = Fees.dynamicFee(e, poolManager, statusB);

    assert statusA.key.fee < statusB.key.fee && statusB.key.fee < MAX_FEE_UNITS() 
        => feeA <= feeB;
}

rule checkFeeAxioms_getAmountIn(PoolStatusManager.PoolStatus status, bool zeroForOne, uint256 amountOut) {
    env e;
    uint256 reserveIn; uint256 reserveOut;
    reserveIn, reserveOut = getReservesByStatus(status, zeroForOne);

    uint256 amountIn; uint24 fee; uint256 feeAmount;
    amountIn, fee, feeAmount = Test.getAmountIn(e, status, zeroForOne, amountOut);

    assert validReservesAndAmounts(amountOut, reserveOut, reserveIn);
    assert feeAmount <= amountOut;
    assert fee <= MAX_FEE_UNITS();
    assert status.key.fee < MAX_FEE_UNITS() => fee < MAX_FEE_UNITS();
}

rule checkFeeAxioms_getAmountOut(PoolStatusManager.PoolStatus status, bool zeroForOne, uint256 amountIn) {
    env e;
    uint256 reserveIn; uint256 reserveOut;
    reserveIn, reserveOut = getReservesByStatus(status, zeroForOne);

    uint256 amountOut; uint24 fee; uint256 feeAmount;
    amountOut, fee, feeAmount = Test.getAmountOut(e, status, zeroForOne, amountIn);

    assert validReservesAndAmounts(amountIn, reserveOut, reserveIn);
    assert fee < MAX_FEE_UNITS() => feeAmount <= amountIn;
    assert status.key.fee == 0 => feeAmount == 0;
    assert fee <= MAX_FEE_UNITS();
    assert status.key.fee < MAX_FEE_UNITS() => fee < MAX_FEE_UNITS();
}