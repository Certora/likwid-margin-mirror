using PoolManager as PM;
using MarginHook as Hook;
using MirrorTokenManager as MT;

methods {
    function PM._swap(int256 amountToSwap) internal returns (int256) => assertZeroDelta(amountToSwap);
    function PM._initializePool(PoolManager.PoolId poolId, uint160 sqrtPriceX96) internal returns int24 => initializePoolCVL(poolId,sqrtPriceX96);

    /// Pure function is summarized by a generic arbitrary mapping - this is logically sound.
    function Hooks.hasPermission(address self, uint160 flag) internal returns (bool) => CVLHasPermission(self, flag);

    function Helper.PoolKeyToId(PoolManager.PoolKey) external returns (PoolManager.PoolId) envfree;
    function Helper.toCurrency(address token) external returns (PoolManager.Currency) envfree;
    function Helper.getPriceX112FromReserves(uint256 _reserve0, uint256 _reserve1) external returns (uint224,uint224) envfree;
    function Helper.toId(PoolManager.Currency) external returns (uint256) envfree;
    function Helper.toTokenId(PoolManager.Currency, PoolManager.PoolKey) external returns (uint256) envfree;
    function PM.balanceOf(address,uint256) external returns (uint256) envfree;
    function MT.balanceOf(address,uint256) external returns (uint256) envfree;
}

definition ONE_TRILLION() returns uint256 = 10^12;

definition MAX_FEE() returns uint24 = 10^6;

definition ValidTimestamp(env e) returns bool = e.block.timestamp > 0 && e.block.timestamp <= max_uint32;

persistent ghost mapping(PoolManager.PoolId => bool) pool_is_initialized {
    init_state axiom forall PoolManager.PoolId poolId. !pool_is_initialized[poolId];
}

/// Source: lib/v4-periphery/lib/v4-core/src/libraries/Hooks.sol
definition BEFORE_SWAP_FLAG() returns uint160 = 1 << 7;
definition AFTER_SWAP_FLAG() returns uint160 = 1 << 6;
definition BEFORE_SWAP_RETURNS_DELTA_FLAG() returns uint160 = 1 << 3;
definition AFTER_SWAP_RETURNS_DELTA_FLAG() returns uint160 = 1 << 2;
definition BEFORE_ADD_LIQUIDITY_FLAG() returns uint160 = 1 << 11;
definition BEFORE_INITIALIZE_FLAG() returns uint160 = 1 << 13;
definition AFTER_INITIALIZE_FLAG() returns uint160 = 1 << 12;

/// Based on Hook.getHookPermissions() - must be verified against the real contract!
persistent ghost CVLHasPermission(address,uint160) returns bool {
    /// Fix the permissions based on the MarginHook.
    axiom CVLHasPermission(Hook, BEFORE_SWAP_FLAG()) == true;
    axiom CVLHasPermission(Hook, BEFORE_SWAP_RETURNS_DELTA_FLAG()) == true;
    axiom CVLHasPermission(Hook, AFTER_SWAP_FLAG()) == false;
    axiom CVLHasPermission(Hook, AFTER_SWAP_RETURNS_DELTA_FLAG()) == false;
    axiom CVLHasPermission(Hook, BEFORE_ADD_LIQUIDITY_FLAG()) == true;
    axiom CVLHasPermission(Hook, BEFORE_INITIALIZE_FLAG()) == true;
    axiom CVLHasPermission(Hook, AFTER_INITIALIZE_FLAG()) == false;
}

definition calledByHook(method f) returns bool = false
    //|| f.selector == sig:PairPoolManager.updateBalances(PairPoolManager.PoolKey).selector
    //|| f.selector == sig:PairPoolManager.setBalances(PoolManager.PoolId).selector
    || f.selector == sig:PairPoolManager.initialize(PairPoolManager.PoolKey).selector;

definition alwaysReverting(method f) returns bool = false
    || f.selector == sig:Hook.beforeRemoveLiquidity(address,PoolManager.PoolKey,IPoolManager.ModifyLiquidityParams,bytes).selector
    || f.selector == sig:Hook.beforeAddLiquidity(address,PoolManager.PoolKey,IPoolManager.ModifyLiquidityParams,bytes).selector
    || f.selector == sig:Hook.afterSwap(address,PoolManager.PoolKey,IPoolManager.SwapParams,PoolManager.BalanceDelta,bytes).selector
    || f.selector == sig:Hook.afterRemoveLiquidity(address,PoolManager.PoolKey,IPoolManager.ModifyLiquidityParams,PoolManager.BalanceDelta,PoolManager.BalanceDelta,bytes).selector
    || f.selector == sig:Hook.afterAddLiquidity(address,PoolManager.PoolKey,IPoolManager.ModifyLiquidityParams,PoolManager.BalanceDelta,PoolManager.BalanceDelta,bytes).selector
    || f.selector == sig:Hook.afterInitialize(address,PoolManager.PoolKey,uint160,int24).selector
    || f.selector == sig:Hook.beforeDonate(address,PoolManager.PoolKey,uint256,uint256,bytes).selector
    || f.selector == sig:Hook.afterDonate(address,PoolManager.PoolKey,uint256,uint256,bytes).selector;

function zeroCurrencyDeltaForAll() returns bool {
    /// Overall require on storage by direct access.
    return forall address token. forall address account. PM._currencyDelta[token][account] == 0;
}

function initializePoolCVL(PoolManager.PoolId poolId, uint160 sqrtPriceX96) returns int24 {
    require !(pool_is_initialized[poolId]);
    pool_is_initialized[poolId] = true;
    return 0;
}

/// Since there is no liquidity in pools in the PoolManager, the hook should never pass a non-zero amount to be swapped.
function assertZeroDelta(int256 amountToSwap) returns int256 {
    assert amountToSwap == 0, "The hook must not pass any amount to the pool swap function";
    return 0;
}

rule validateCalledByHook(method f) filtered{f -> calledByHook(f)} {
    env e;
    calldataarg args;
    address _hooks = PairPoolManager.hooks;
    f(e, args);
    assert e.msg.sender == _hooks;
}

rule validateUnlockCallbackSender() {
    env e;
    calldataarg args;
    address _poolManager = PairPoolManager.poolManager;
    PairPoolManager.unlockCallback(e, args);
    assert _poolManager == e.msg.sender;
}

/// Auxiliary getters of token IDs from status store poolId.

function currency0IdFromPoolId(PoolManager.PoolId poolId) returns uint256 {
    return Helper.toId(PoolStatusManager.statusStore[poolId].key.currency0);
}

function currency1IdFromPoolId(PoolManager.PoolId poolId) returns uint256 {
    return Helper.toId(PoolStatusManager.statusStore[poolId].key.currency1);
}

function currency0TokenIdFromPoolId(PoolManager.PoolId poolId) returns uint256 {
    return Helper.toTokenId(PoolStatusManager.statusStore[poolId].key.currency0, PoolStatusManager.getKey(poolId));
}

function currency1TokenIdFromPoolId(PoolManager.PoolId poolId) returns uint256 {
    return Helper.toTokenId(PoolStatusManager.statusStore[poolId].key.currency1, PoolStatusManager.getKey(poolId));
}

/// @title Valid status store for pools
invariant ValidStatusInitializedPools(PoolManager.PoolId poolId)
    (pool_is_initialized[poolId] => (/// Initialized
        PoolStatusManager.statusStore[poolId].rate0CumulativeLast >= ONE_TRILLION() &&
        PoolStatusManager.statusStore[poolId].rate1CumulativeLast >= ONE_TRILLION() &&
        PoolStatusManager.statusStore[poolId].blockTimestampLast > 0 &&
        PoolStatusManager.statusStore[poolId].key.hooks == Hook &&
        PoolStatusManager.statusStore[poolId].key.currency1 > 0 &&
        PoolStatusManager.statusStore[poolId].key.currency1 > PoolStatusManager.statusStore[poolId].key.currency0 &&
            ///
            PoolStatusManager.statusStore[poolId].realReserve0 <= PM.balanceOf(PairPoolManager, currency0IdFromPoolId(poolId)) &&
            PoolStatusManager.statusStore[poolId].realReserve1 <= PM.balanceOf(PairPoolManager, currency1IdFromPoolId(poolId)) &&
            PoolStatusManager.statusStore[poolId].mirrorReserve0  <= MT.balanceOf(PairPoolManager, currency0TokenIdFromPoolId(poolId)) &&
            PoolStatusManager.statusStore[poolId].mirrorReserve1  <= MT.balanceOf(PairPoolManager, currency1TokenIdFromPoolId(poolId)) &&
            ///
        PoolStatusManager.statusStore[poolId].key.fee <= MAX_FEE() &&
        Helper.PoolKeyToId(PoolStatusManager.getKey(poolId)) == poolId))
    &&
    (!pool_is_initialized[poolId] => (/// Uninitialized
        PoolStatusManager.statusStore[poolId].rate0CumulativeLast == 0 &&
        PoolStatusManager.statusStore[poolId].rate1CumulativeLast == 0 &&
        PoolStatusManager.statusStore[poolId].blockTimestampLast == 0 &&
        PoolStatusManager.statusStore[poolId].realReserve0 == 0 &&
        PoolStatusManager.statusStore[poolId].realReserve1 == 0 &&
        PoolStatusManager.statusStore[poolId].mirrorReserve0 == 0 &&
        PoolStatusManager.statusStore[poolId].mirrorReserve1 == 0 &&
        PoolStatusManager.statusStore[poolId].lendingRealReserve0 == 0 &&
        PoolStatusManager.statusStore[poolId].lendingRealReserve1 == 0 &&
        PoolStatusManager.statusStore[poolId].lendingMirrorReserve0 == 0 &&
        PoolStatusManager.statusStore[poolId].lendingMirrorReserve1 == 0 &&
        PoolStatusManager.statusStore[poolId].key.hooks == 0 &&
        PoolStatusManager.statusStore[poolId].key.currency1 == 0 &&
        PoolStatusManager.statusStore[poolId].key.currency0 == 0 &&
        PoolStatusManager.statusStore[poolId].key.fee == 0))
    {
        preserved with (env e) {
            //require pool_is_initialized[poolId];
            require ValidTimestamp(e);
            requireInvariant ValidStatusInitializedPools(PoolID1);
            requireInvariant ValidStatusInitializedPools(PoolID2);
        }
    }

/// @title Unlocking the PoolManager in removeLiquidity() should always result in zeroed-out virtual accounting.
rule removeLiquidityEndsWithZeroVirtualAccounting()
{
    env e;
    PairPoolManager.RemoveLiquidityParams params;
    requireInvariant ValidStatusInitializedPools(params.poolId);
    
    require zeroCurrencyDeltaForAll();
        PairPoolManager.removeLiquidity(e, params);
    assert zeroCurrencyDeltaForAll();
}

/// @title Unlocking the PoolManager in addLiquidity() should always result in zeroed-out virtual accounting.
rule addLiquidityEndsWithZeroVirtualAccounting()
{
    env e;
    require e.msg.sender != PM;
    PairPoolManager.AddLiquidityParams params;
    requireInvariant ValidStatusInitializedPools(params.poolId);
    
    require zeroCurrencyDeltaForAll();
        PairPoolManager.addLiquidity(e, params);
    assert zeroCurrencyDeltaForAll();
}

/// @title Unlocking the PoolManager in release() should always result in zeroed-out virtual accounting.
rule releaseEndsWithZeroVirtualAccounting()
{
    env e;
    require e.msg.sender != PM;
    PairPoolManager.ReleaseParams params;
    require params.payer != PM;
    PoolStatusManager.PoolStatus status;
    require Helper.PoolKeyToId(status.key) == params.poolId;
    requireInvariant ValidStatusInitializedPools(params.poolId);
    
    require zeroCurrencyDeltaForAll();
        PairPoolManager.release(e, status, params);
    assert zeroCurrencyDeltaForAll();
}

/// @title Unlocking the PoolManager in collectProtocolFees() should always result in zeroed-out virtual accounting.
rule collectProtocolFeesEndsWithZeroVirtualAccounting()
{
    env e;
    require e.msg.sender != PM;
    calldataarg args;
    
    require zeroCurrencyDeltaForAll();
        PairPoolManager.collectProtocolFees(e, args);
    assert zeroCurrencyDeltaForAll();
}

/// @title Unlocking the PoolManager in swapMirror() should always result in zeroed-out virtual accounting.
rule swapMirrorEndsWithZeroVirtualAccounting()
{
    env e;
    require e.msg.sender != PM;
    address sender;
    address recipient; 
    PoolManager.PoolId poolId; 
    bool zeroForOne; 
    uint256 amountIn;
    requireInvariant ValidStatusInitializedPools(poolId);
    require sender != PM;
    
    require zeroCurrencyDeltaForAll();
        PairPoolManager.swapMirror(e, sender, recipient, poolId, zeroForOne, amountIn);
    assert zeroCurrencyDeltaForAll();
}

/// @title Unlocking the PoolManager in margin() should always result in zeroed-out virtual accounting.
rule marginEndsWithZeroVirtualAccounting()
{
    env e;
    require e.msg.sender != PM;
    address sender;
    PoolStatusManager.PoolStatus status;
    PairPoolManager.MarginParamsVo paramsVo;
    require sender != PM;
    require Helper.PoolKeyToId(status.key) == paramsVo.params.poolId;
    requireInvariant ValidStatusInitializedPools(paramsVo.params.poolId);
    
    require zeroCurrencyDeltaForAll();
        //env eSync;
        //PM.sync(eSync, Helper.toCurrency(PM._synchedCurrency));
        PairPoolManager.margin(e, sender, status, paramsVo);
    assert zeroCurrencyDeltaForAll();
}