// SPDX-License-Identifier: MIT

pragma solidity >=0.8.0;

/**
    @dev AMM Hooks contracts must implement this entire interface.
         When an AMM hook is set, the AMM approves the hook to transfer the collateral token.
 */
interface IAmmHooks {
    /**
        @notice AMM association hook
        @dev Called by the AMM, after the AMM approves the hook to transfer the collateral token
     */
    function on_add_hook(address market, address amm) external;

    /**
        @notice
        @dev called by the AMM, prior to the AMM revoking the hook's approval on the collateral token
     */
    function on_remove_hook() external;

    /**
        @dev Called by the controller or AMM, prior to transferring `amount` tokens out of the AMM.
             Upon completing this call, the AMM must hold a balance of at least `amount` tokens.
     */
    function before_collateral_out(uint256 amount) external;

    /**
        @dev Called by the controller or AMM after transferring `amount` tokens into the AMM.
     */
    function after_collateral_in(uint256 amount) external;

    /**
        @dev Gets the total collateral balance for the AMM
     */
    function collateral_balance() external view returns (uint256);
}
