import "./CVLERC20.spec";
import "./MathSummary.spec";
import "./PoolManager.spec";
import "./PoolStatusManager.spec";
import "./getAmountsSummary.spec";

using PairPoolManager as PairPoolManager;
using LendingPoolManager as LendingPoolManager;
using MirrorTokenManager as MirrorTokenManager;
using MarginLiquidity as MarginLiquidity;
using Fallback as Fallback;
using PoolManager as PoolManager;

methods {
    /// Unresolved unlock callback:
    function _.unlockCallback(bytes) external => DISPATCHER(true);

    /// Unresolved unlock callback in PM:
    unresolved external in PoolManager.unlock(bytes) => DISPATCH [
        PairPoolManager.unlockCallback(bytes),
        LendingPoolManager.unlockCallback(bytes)
    ] default HAVOC_ECF;
    /// Unresolved unlock callbacks (PairPoolManager):
    unresolved external in PairPoolManager.unlockCallback(bytes) => DISPATCH [
        PairPoolManager.handleRelease(PoolStatusManager.PoolStatus,PairPoolManager.ReleaseParams),
        PairPoolManager.handleAddLiquidity(address,PoolManager.PoolKey,uint256,uint256),
        PairPoolManager.handleRemoveLiquidity(address,PoolManager.PoolKey,uint256,uint256),
        PairPoolManager.handleMargin(address,address,PoolStatusManager.PoolStatus,PairPoolManager.MarginParamsVo),
        PairPoolManager.handleSwapMirror(address,PoolManager.Currency,uint256),
        PairPoolManager.handleCollectFees(address,PoolManager.Currency ,uint256)
    ] default HAVOC_ECF;
    /// Unresolved unlock callbacks (LendingPoolManager):
    unresolved external in LendingPoolManager.unlockCallback(bytes) => DISPATCH [
        LendingPoolManager.handleWithdraw(address,address,PoolManager.PoolId,PoolManager.Currency,uint256),
        LendingPoolManager.handleDeposit(address,address,PoolManager.PoolId,PoolManager.Currency,uint256)
    ] default HAVOC_ECF;


    //  we don't have an implementation around for `IMarginOracleReader`, it seems
    function _.observeNow(address /*IPairPoolManager*/, PoolStatusManager.PoolStatus /*status*/) external 
        => observeNowCVL() expect (uint224, uint256);


    //  we don't have an implementation around for `IMarginOracleWriter`, it seems
    function _.write(PoolManager.PoolKey /*calldata*/ key, uint112 reserve0, uint112 reserve1) external 
        => NONDET; // TODO model side effects


    // declared in `IStatusBase`, we have the implementation in `PoolStatusManager <: IPoolStatusManager <: IStatusBase`
    // this is called on `e.msg.sender` in places, not sure how to link, so doing a manual dispatcher
    function _.pairPoolManager() external /* view returns (address) */ 
        => pairPoolManagerCVL(calledContract) expect address;

    /// Has only internal effects in MirrorTokenManager.
    function _.setOperator(address,bool) external => NONDET UNRESOLVED;

    function _.marginLiquidity() external => DISPATCHER(true) UNRESOLVED;
    function _.statusManager() external => DISPATCHER(true) UNRESOLVED;
    function _.getMarginReserves(address, PoolManager.PoolId, PoolStatusManager.PoolStatus) external => NONDET UNRESOLVED;
    function _.getInterestReserves(address, PoolManager.PoolId, PoolStatusManager.PoolStatus) external => NONDET UNRESOLVED;
}

methods {
    function PoolStatusManager.getAmountOut(PoolStatusManager.PoolStatus status, bool zeroForOne, uint256 amountIn) external returns (uint256,uint24,uint256) with (env e)
        => getAmountOutCVL(e.block.timestamp, status, zeroForOne, amountIn) DELETE;

    function PoolStatusManager.getAmountIn(PoolStatusManager.PoolStatus status, bool zeroForOne, uint256 amountOut) external returns (uint256,uint24,uint256) with (env e)
        => getAmountInCVL(e.block.timestamp, status, zeroForOne, amountOut) DELETE;

    function _.getAmountOut(PoolStatusManager.PoolStatus status, bool zeroForOne, uint256 amountIn) external with (env e)
        => getAmountOutCVL(e.block.timestamp, status, zeroForOne, amountIn) expect (uint256,uint24,uint256);

    function _.getAmountIn(PoolStatusManager.PoolStatus status, bool zeroForOne, uint256 amountOut) external with (env e)
        => getAmountInCVL(e.block.timestamp, status, zeroForOne, amountOut) expect (uint256,uint24,uint256);

    function MarginFees.getBorrowRateCumulativeLast(PoolStatusManager.PoolStatus) external returns (uint256,uint256)
       => NONDET;

    function MarginLiquidity.getInterestReserves(address, PairPoolManager.PoolId, PairPoolManager.PoolStatus) external returns (uint256, uint256)
        => NONDET;

    function PoolStatusManager._updateInterest0(PairPoolManager.PoolStatus memory, uint256, uint256) internal returns (PairPoolManager.InterestBalance memory) 
        => interestBalanceCVL();

    function PoolStatusManager._updateInterest1(PairPoolManager.PoolStatus memory, uint256, uint256) internal returns (PairPoolManager.InterestBalance memory) 
        => interestBalanceCVL();

    function PoolStatusManager._updateInterests(PairPoolManager.PoolStatus storage) internal 
        => noOp();
}

definition isUnlockCallback(method f) returns bool = 
    f.selector == sig:LendingPoolManager.unlockCallback(bytes).selector ||
    f.selector == sig:PairPoolManager.unlockCallback(bytes).selector;

definition hardMethods(method f) returns bool = 
    f.selector == sig:PairPoolManager.addLiquidity(PairPoolManager.AddLiquidityParams).selector ||
    f.selector == sig:PairPoolManager.removeLiquidity(PairPoolManager.RemoveLiquidityParams).selector ||
    f.selector == sig:PairPoolManager.swapMirror(address,address,PoolManager.PoolId,bool,uint256).selector ||
    f.selector == sig:PairPoolManager.mirrorInRealOut(PoolManager.PoolId,PoolManager.Currency,uint256).selector;
    
function noOp() {}

function interestBalanceCVL() returns PairPoolManager.InterestBalance {

    PairPoolManager.InterestBalance res;

    require res.allInterest == 0;
    require res.pairInterest == 0;
    require res.lendingInterest == 0;
    require res.protocolInterest == 0;

    return res;
}

function observeNowCVL() returns (uint224, uint256) {
    uint224 nondet1;
    uint256 nondet2;
    return (nondet1, nondet2);
}

function pairPoolManagerCVL(address callee) returns address {
    if (callee == PoolStatusManager) {
        return PoolStatusManager.pairPoolManager; 
    } else if(callee == LendingPoolManager) {
        return LendingPoolManager.pairPoolManager;
    } else {
        assert false;
        return 0;
    }
}

/*
 * @title The rate cumulative last value can never decrease, for any pool.
 * @status Verified
 * @notice 
 * @report https://prover.certora.com/output/497546/70bcde5011d345e4a42802e4b2c77523?anonymousKey=cb4fa9d98c65c525cedcadb095e2cb0b2102faf6
 */
rule rateCumulativeCannotDecrease(PoolManager.PoolId poolId, method f) 
filtered{f -> !f.isView && f.contract == PairPoolManager && !isUnlockCallback(f)} {
    requireInvariant ValidStatusInitializedPools(poolId);
    mathint rateCumulative0_pre = PoolStatusManager.statusStore[poolId].rate0CumulativeLast;
    mathint rateCumulative1_pre = PoolStatusManager.statusStore[poolId].rate1CumulativeLast;
        env e;
        calldataarg args;
        f(e, args);
    mathint rateCumulative0_post = PoolStatusManager.statusStore[poolId].rate0CumulativeLast;
    mathint rateCumulative1_post = PoolStatusManager.statusStore[poolId].rate1CumulativeLast;

    assert rateCumulative1_post >= rateCumulative1_pre && rateCumulative0_post >= rateCumulative0_pre;
}

/*
 * @title the addLiquidity method does not affect the getAmountIn values of other pools.
 * @status Verified
 * @notice 
 * @report https://prover.certora.com/output/497546/c15cf072da6f4182b00a2f08bda6df13?anonymousKey=b2be7fb72a743fc965643b656fa28a890179c52c
 */
rule addingLiquidityHasZeroEffectOnOtherPools(PoolManager.PoolId poolId, bool zeroForOne)
{
    env e;
    uint256 reserve0;
    uint256 reserve1;
    reserve0, reserve1 = getReserves(e, poolId);
    uint256 quote_amount = assert_uint256(min((zeroForOne ? reserve1 : reserve0)/2, 10^6));

    uint256 amountIn_pre = PairPoolManager.getAmountIn(e, poolId, zeroForOne, quote_amount);
        PairPoolManager.AddLiquidityParams params;
        requireInvariant ValidStatusInitializedPools(params.poolId);
        requireInvariant ValidStatusInitializedPools(poolId);
        PairPoolManager.addLiquidity(e, params);
    uint256 amountIn_post = PairPoolManager.getAmountIn(e, poolId, zeroForOne, quote_amount);

    assert params.poolId != poolId => amountIn_post == amountIn_pre;
}

/*
 * @title the removeLiquidity method does not affect the getAmountIn values of other pools.
 * @status Verified
 * @notice 
 * @report https://prover.certora.com/output/497546/7fdeaee015ab414d8d0234789598ea47?anonymousKey=90d3c8a1feae75e1239bc559bd3e06e6c6e4d084
 */
rule removingLiquidityHasZeroEffectOnOtherPools(PoolManager.PoolId poolId, bool zeroForOne)
{
    env e;
    uint256 reserve0;
    uint256 reserve1;
    reserve0, reserve1 = getReserves(e, poolId);
    uint256 quote_amount = assert_uint256(min((zeroForOne ? reserve1 : reserve0)/2, 10^6));

    uint256 amountIn_pre = PairPoolManager.getAmountIn(e, poolId, zeroForOne, quote_amount);
        PairPoolManager.RemoveLiquidityParams params;
        requireInvariant ValidStatusInitializedPools(params.poolId);
        requireInvariant ValidStatusInitializedPools(poolId);
        PairPoolManager.removeLiquidity(e, params);
    uint256 amountIn_post = PairPoolManager.getAmountIn(e, poolId, zeroForOne, quote_amount);

    assert params.poolId != poolId => amountIn_post == amountIn_pre;
}

/// @title addLiquidity() shouldn't change the price by more than the allowed error.
/// below rule is work in progress; issues: rule fails because the bound is too strict  
rule addLiquidityPriceStability(PoolManager.PoolId poolId, bool zeroForOne) 
{
    env e;
    uint256 reserve0_pre;
    uint256 reserve1_pre;
    uint224 price0X112_pre;
    uint224 price1X112_pre;
    reserve0_pre, reserve1_pre = PairPoolManager.getReserves(e, poolId);
    price0X112_pre, price1X112_pre = Helper.getPriceX112FromReserves(reserve0_pre, reserve1_pre);

        PairPoolManager.AddLiquidityParams params;
        require params.poolId == poolId;
        requireInvariant ValidStatusInitializedPools(params.poolId);
        PairPoolManager.addLiquidity(e, params);

    uint256 reserve0_post;
    uint256 reserve1_post;
    uint224 price0X112_post;
    uint224 price1X112_post;
    reserve0_post, reserve1_post = PairPoolManager.getReserves(e, poolId);
    price0X112_post, price1X112_post = Helper.getPriceX112FromReserves(reserve0_post, reserve1_post);

    assert abs(price0X112_post - price0X112_pre) <= 2;
    assert abs(price1X112_post - price1X112_pre) <= 2;
}

/// @title removeLiquidity() shouldn't change the price by more than the allowed error.
/// below rule is work in progress; issues: timeout
rule removeLiquidityPriceStability(PoolManager.PoolId poolId, bool zeroForOne) 
{
    env e;
    uint256 reserve0_pre;
    uint256 reserve1_pre;
    uint224 price0X112_pre;
    uint224 price1X112_pre;
    reserve0_pre, reserve1_pre = PairPoolManager.getReserves(e, poolId);
    price0X112_pre, price1X112_pre = Helper.getPriceX112FromReserves(reserve0_pre, reserve1_pre);

        PairPoolManager.RemoveLiquidityParams params;
        require params.poolId == poolId;
        requireInvariant ValidStatusInitializedPools(params.poolId);
        PairPoolManager.removeLiquidity(e, params);
    
    uint256 reserve0_post;
    uint256 reserve1_post;
    uint224 price0X112_post;
    uint224 price1X112_post;
    reserve0_post, reserve1_post = PairPoolManager.getReserves(e, poolId);
    price0X112_post, price1X112_post = Helper.getPriceX112FromReserves(reserve0_post, reserve1_post);

    assert abs(price0X112_post - price0X112_pre) <= 2;
    assert abs(price1X112_post - price1X112_pre) <= 2;
}

// excluding methods whose body is just `revert <msg>';
use builtin rule sanity filtered{ f -> 
    !alwaysReverting(f) 
        && f.contract != PM 
        && f.contract == currentContract
}

function getAllBalances(env e, PairPoolManager.PoolKey key, uint256 poolId)
    returns (uint256, uint256, uint256, uint256, uint256) 
{
    uint256 currency0ID = Helper.toId(key.currency0);
    uint256 currency1ID = Helper.toId(key.currency1);
    uint256 currency0TokenID = Helper.toTokenId(key.currency0, key);
    uint256 currency1TokenID = Helper.toTokenId(key.currency1, key);

    uint256 totalSupply = MarginLiquidity.balanceOf(e, PairPoolManager, poolId);
    uint256 realReserve0 = PoolManager.balanceOf(PairPoolManager, currency0ID);
    uint256 realReserve1 = PoolManager.balanceOf(PairPoolManager, currency1ID);
    uint256 mirrorReserve0 = MirrorTokenManager.balanceOf(PairPoolManager, currency0TokenID);
    uint256 mirrorReserve1 = MirrorTokenManager.balanceOf(PairPoolManager, currency1TokenID);

    return (totalSupply, realReserve0, realReserve1, mirrorReserve0, mirrorReserve1);
}

/*
 * @title addLiquidity does not decrease the real reserves and does not change mirror reserves. 
 * @status Verified
 * @notice 
 * @report https://prover.certora.com/output/497546/bcdca06c65574489b4c9cfc6a43627b2?anonymousKey=d1222b8a6af84d6b2d6863cb7b0ef3ce813765e5
 */
rule integrityOfAddLiquidity() {
    env e;
    PairPoolManager.AddLiquidityParams params;
    uint256 poolId = MarginLiquidity.getPoolId(e, params.poolId);

    require e.msg.sender == Fallback;

    PairPoolManager.PoolKey key = PoolStatusManager.getKey(params.poolId);

    uint256 preTotalSupply;
    uint256 preRealReserve0; 
    uint256 preRealReserve1;
    uint256 preMirrorReserve0; 
    uint256 preMirrorReserve1;
    (preTotalSupply, preRealReserve0, preRealReserve1, preMirrorReserve0, preMirrorReserve1) 
        = getAllBalances(e, key, poolId);

    addLiquidity(e, params);

    uint256 postTotalSupply;
    uint256 postRealReserve0; 
    uint256 postRealReserve1;
    uint256 postMirrorReserve0; 
    uint256 postMirrorReserve1;
    (postTotalSupply, postRealReserve0, postRealReserve1, postMirrorReserve0, postMirrorReserve1) 
        = getAllBalances(e, key, poolId);

    assert preTotalSupply <= postTotalSupply;
    assert preRealReserve0 <= postRealReserve0;
    assert preRealReserve1 <= postRealReserve1;
    assert preMirrorReserve0 == postMirrorReserve0;
    assert preMirrorReserve1 == postMirrorReserve1;
}

/*
 * @title removeLiquidity does not increase the real reserves and does not change mirror reserves. 
 * @status Verified
 * @notice 
 * @report https://prover.certora.com/output/497546/7fdeaee015ab414d8d0234789598ea47?anonymousKey=90d3c8a1feae75e1239bc559bd3e06e6c6e4d084
 */
rule integrityOfRemoveLiquidity() {
    env e;
    PairPoolManager.RemoveLiquidityParams params;
    uint256 poolId = MarginLiquidity.getPoolId(e, params.poolId);

    require e.msg.sender == Fallback;

    PairPoolManager.PoolKey key = PoolStatusManager.getKey(params.poolId);

    uint256 preTotalSupply;
    uint256 preRealReserve0; 
    uint256 preRealReserve1;
    uint256 preMirrorReserve0; 
    uint256 preMirrorReserve1;
    (preTotalSupply, preRealReserve0, preRealReserve1, preMirrorReserve0, preMirrorReserve1) 
        = getAllBalances(e, key, poolId);

    removeLiquidity(e, params);

    uint256 postTotalSupply;
    uint256 postRealReserve0; 
    uint256 postRealReserve1;
    uint256 postMirrorReserve0; 
    uint256 postMirrorReserve1;
    (postTotalSupply, postRealReserve0, postRealReserve1, postMirrorReserve0, postMirrorReserve1) 
        = getAllBalances(e, key, poolId);

    assert preTotalSupply >= postTotalSupply;
    assert preRealReserve0 >= postRealReserve0;
    assert preRealReserve1 >= postRealReserve1;
    assert preMirrorReserve0 == postMirrorReserve0;
    assert preMirrorReserve1 == postMirrorReserve1;
}

/*
 * @title setBalance() followed updateBalance() does not change the balances
 * @status Verified after fix
 * @notice 
 * @report https://prover.certora.com/output/497546/f8bac2eebb7941bbb357e6d5c370e3b3?anonymousKey=4a139a9a266349fd26a60c26ae13ef15559e68e1
 */
rule intergrityOfSetAndUpdateBalances() {
    env e;
    PairPoolManager.PoolId poolId;
    bool b;

    uint256 uPoolId = MarginLiquidity.getPoolId(e, poolId);
    PairPoolManager.PoolKey key = PoolStatusManager.getKey(poolId);

    uint256 preTotalSupply;
    uint256 preRealReserve0; 
    uint256 preRealReserve1;
    uint256 preMirrorReserve0; 
    uint256 preMirrorReserve1;
    (preTotalSupply, preRealReserve0, preRealReserve1, preMirrorReserve0, preMirrorReserve1) 
        = getAllBalances(e, key, uPoolId);

    PoolStatusManager.setBalances(e, poolId);
    PoolStatusManager.update(e, poolId, b);

    uint256 postTotalSupply;
    uint256 postRealReserve0; 
    uint256 postRealReserve1;
    uint256 postMirrorReserve0; 
    uint256 postMirrorReserve1;
    (postTotalSupply, postRealReserve0, postRealReserve1, postMirrorReserve0, postMirrorReserve1) 
        = getAllBalances(e, key, uPoolId);

    assert preRealReserve0 == postRealReserve0;
    assert preRealReserve1 == postRealReserve1;
    assert preMirrorReserve0 == postMirrorReserve0;
    assert preMirrorReserve1 == postMirrorReserve1;
}

/*
 * @title his rule demonstrates how retainSupply can grow bigger than the totalSupply
 * @status Violated
 * @notice 
 * @report https://prover.certora.com/output/497546/fa08a13d5e3e41a782991f0917016f03?anonymousKey=094bbcee75ecd6785ea7c864b1ae3cca3c753637
 */
rule integrityOfTotalSupply() {
    env e;
    uint256 uPoolId;

    uint256 preTotalSupply;
    uint256 preRetainSupply0;
    (preTotalSupply, preRetainSupply0, _) = MarginLiquidity.getSupplies(e, uPoolId);

    require preRetainSupply0 <= preTotalSupply;

    address receiver;
    uint256 id;
    uint256 amount;
    MarginLiquidity.transfer(e, receiver, id, amount);

    uint256 postTotalSupply;
    uint256 postRetainSupply0;
    (postTotalSupply, postRetainSupply0, _) = MarginLiquidity.getSupplies(e, uPoolId);

    assert  postRetainSupply0 <= postTotalSupply;
}