using PoolManager as PM;

methods {
    function PM._swap(int256 amountToSwap) internal returns (int256) => assertZeroDelta(amountToSwap);
    /// Pure function is summarized by a generic arbitrary mapping - this is logically sound.
    function Hooks.hasPermission(address self, uint160 flag) internal returns (bool) => CVLHasPermission(self, flag);
}

definition BEFORE_SWAP_FLAG() returns uint160 = 1 << 7;
definition AFTER_SWAP_FLAG() returns uint160 = 1 << 6;
definition BEFORE_SWAP_RETURNS_DELTA_FLAG() returns uint160 = 1 << 3;
definition AFTER_SWAP_RETURNS_DELTA_FLAG() returns uint160 = 1 << 2;
definition BEFORE_ADD_LIQUIDITY_FLAG() returns uint160 = 1 << 11;

persistent ghost CVLHasPermission(address,uint160) returns bool {
    /// Fix the permissions based on the MarginHookManager.
    axiom CVLHasPermission(MarginHookManager, BEFORE_SWAP_FLAG()) == true;
    axiom CVLHasPermission(MarginHookManager, BEFORE_SWAP_RETURNS_DELTA_FLAG()) == true;
    axiom CVLHasPermission(MarginHookManager, AFTER_SWAP_FLAG()) == false;
    axiom CVLHasPermission(MarginHookManager, AFTER_SWAP_RETURNS_DELTA_FLAG()) == false;
    axiom CVLHasPermission(MarginHookManager, BEFORE_ADD_LIQUIDITY_FLAG()) == true;
}

function zeroCurrencyDeltaForAll() returns bool {
    /// Overall require on storage by direct access.
    return forall address token. forall address account. PM._currencyDelta[token][account] == 0;
}

function assertZeroDelta(int256 amountToSwap) returns int256 {
    assert amountToSwap == 0, "The hook must not pass any amount to the pool swap function";
    return 0;
}

/// @title Unlocking the PoolManager in removeLiquidity() should always result in zeroed-out virtual accounting.
rule removeLiquidityEndsWithZeroVirtualAccounting()
{
    env e;
    MarginHookManager.RemoveLiquidityParams params;
    require MarginHookManager.hookStatusStore[params.poolId].key.hooks == MarginHookManager;
    
    require zeroCurrencyDeltaForAll();
        MarginHookManager.removeLiquidity(e, params);
    assert zeroCurrencyDeltaForAll();
    /// Easier to debug
    //address token;
    //address account;
    //assert PM._currencyDelta[token][account] == 0;
}

/// @title Unlocking the PoolManager in addLiquidity() should always result in zeroed-out virtual accounting.
rule addLiquidityEndsWithZeroVirtualAccounting()
{
    env e;
    MarginHookManager.AddLiquidityParams params;
    require MarginHookManager.hookStatusStore[params.poolId].key.hooks == MarginHookManager;
    
    require zeroCurrencyDeltaForAll();
        MarginHookManager.addLiquidity(e, params);
    assert zeroCurrencyDeltaForAll();
}

/// @title Unlocking the PoolManager in release() should always result in zeroed-out virtual accounting.
rule releaseEndsWithZeroVirtualAccounting()
{
    env e;
    MarginHookManager.ReleaseParams params;
    require MarginHookManager.hookStatusStore[params.poolId].key.hooks == MarginHookManager;
    
    require zeroCurrencyDeltaForAll();
        MarginHookManager.release(e, params);
    assert zeroCurrencyDeltaForAll();
}