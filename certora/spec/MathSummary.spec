import "./CVLMath.spec";
/*
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Summarization of Open-Zeppelin Math library (optimistic, requires denominator is non-zero)                                                                                  
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
*/

methods {
    function Math.mulDiv(uint256 x, uint256 y, uint256 denominator, Math.Rounding rounding) internal returns (uint256) =>
        // mulDivCVL_pessim(x,y,denominator,rounding);
        mulDivCVL(x,y,denominator,rounding);    

    function Math.mulDiv(uint256 x, uint256 y, uint256 denominator) internal returns (uint256) =>
        // mulDivDownCVL_pessim(x,y,denominator);
        // mulDivLIA(x,y,denominator);
        mulDivDownCVL(x,y,denominator);

    function Math.average(uint256 a, uint256 b) internal returns (uint256) => averageCVL(a,b);
    
    function Math.sqrt(uint256 a) internal returns (uint256) => sqrtCVL(a);
}

/// Linear over-approximation for mulDiv()
ghost mulDivLIA(uint256,uint256,uint256) returns uint256
{
    axiom forall uint256 x. forall uint256 y.
        mulDivLIA(0, x, y) == 0 && mulDivLIA(x, 0 ,y) == 0;
    axiom forall uint256 x. forall uint256 y. forall uint256 z.
        (y > z => mulDivLIA(x,y,z) >= x) &&
        (x > z => mulDivLIA(x,y,z) >= y) &&
        (y == z => mulDivLIA(x,y,z) == x) &&
        (x == z => mulDivLIA(x,y,z) == y) &&
        (mulDivLIA(x,y,z) == mulDivLIA(y,x,z));
    axiom forall uint256 x1. forall uint256 x2. forall uint256 y. forall uint256 z.
        x1 < x2 => 
            mulDivLIA(x1, y, z) <= mulDivLIA(x2, y, z) &&
            mulDivLIA(y, x1, z) <= mulDivLIA(y, x2, z) &&
            mulDivLIA(y, z, x2) <= mulDivLIA(y, z, x1);
}