import "./CVLERC20.spec";
import "./PoolManager.spec";

methods {
    /// Unresolved unlock callback in PM:
    unresolved external in PoolManager.unlock(bytes) => DISPATCH [
        MarginHookManager.unlockCallback(bytes)
    ] default HAVOC_ECF;
    
    /// Unresolved unlock callback:
    function _.unlockCallback(bytes) external => DISPATCHER(true);

    /// Unresolved unlock callbacks:
    unresolved external in MarginHookManager.unlockCallback(bytes) => DISPATCH [
        MarginHookManager.handleRelease(MarginHookManager.ReleaseParams),
        MarginHookManager.handleAddLiquidity(address,PoolManager.PoolKey,uint256,uint256),
        MarginHookManager.handleMargin(address,MarginHookManager.MarginParams)
    ] default HAVOC_ECF;

    function _.onERC721Received(
        address operator,
        address from,
        uint256 tokenId,
        bytes data
    ) external => NONDET; /* expects bytes4 */


    // summaries for dealing with nonlinear arithmetic
    // function MarginHookManager._getAmountIn(MarginHookManager.HookStatus memory status, bool zeroForOne, uint256 amountOut) internal returns (uint256) 
    //     => NONDET;

    // function _estimatePNL(MarginHookManager.MarginPosition memory _position, uint256 closeMillionth) internal returns (int256)
    //      => NONDET;

    // function getPosition(uint256 positionId) internal returns (MarginHookManager.MarginPosition memory)
    //     => <cvl-summarize? -- can't NONDET it because of struct> ;

    // function MarginFees.getBorrowRateByReserves(uint256 realReserve, uint256 mirrorReserve) internal returns (uint256) 
    //     => NONDET;
}

// excluding methods whose body is just `revert <msg>;
use builtin rule sanity filtered { f -> f.contract == currentContract } 

