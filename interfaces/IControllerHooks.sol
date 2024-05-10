// SPDX-License-Identifier: MIT

pragma solidity >=0.8.0;

/**
    @dev Controller hooks are set per-function. Controller Hooks contracts must
         only implement the interfaces of the hooks which will be active.

         For each active hook, the contract should implement both nonpayable
         and view versions of the required method.

         Each function returns `int256 debtAdjustment`.
         * A positive value creates more debt, charging a fee to the account.
         * A negative value creates less debt, giving a rebate to the account.

         Note that the sum of all hook debt adjustments for a market cannot be
         less than zero. You can check the current debt adjustment sum using
         `MainController.get_total_hook_debt_adjustment`
 */
interface IControllerHooks {
    /**
        @dev Called when creating a new loan
        @return debtAdjustment Adjustment amount to the new debt created
                * The minted amount is exactly `debtAmount`
                * The adjustment is applied to the amount of debt owed to the market
                * Reverts if `debtAmount - debtAdjustment < 0`
     */
    function on_create_loan(
        address account,
        address market,
        uint256 collAmount,
        uint256 debtAmount
    ) external returns (int256 debtAdjustment);

    function on_create_loan_view(
        address account,
        address market,
        uint256 collAmount,
        uint256 debtAmount
    ) external view returns (int256 debtAdjustment);

    /**
        @dev Called when adjusting an existing loan
        @return debtAdjustment Debt adjustment amount
                * The change to debt is exactly `debtChange`. A positive value means minting, negative burning.
                * The adjustment is applied to the amount of debt owed to the market.
                * Reverts if `debtChange == 0 && debtAdjustment != 0`
                * Reverts if the sign of `debtChange` and `debtChange + debtAdjustment` are different
     */
    function on_adjust_loan(
        address account,
        address market,
        int256 collChange,
        int256 debtChange
    ) external returns (int256 debtAdjustment);

    function on_adjust_loan_view(
        address account,
        address market,
        int256 collChange,
        int256 debtChange
    ) external returns (int256 debtAdjustment);

    /**
        @dev Called when closing an existing loan
        @return debtAdjustment Adjustment amount on debt owed
                * The amount of debt reduced is exactly `accountDebt`
                * The adjustment is applied to the amount of tokens burned from the caller's address
                * Reverts if `accountDebt - debtAdjustment < 0`
     */
    function on_close_loan(
        address account,
        address market,
        uint256 accountDebt
    ) external returns (int256 debtAdjustment);

    function on_close_loan_view(
        address account,
        address market,
        uint256 accountDebt
    ) external view returns (int256 debtAdjustment);

    /**
        @dev Called when an existing loan is liquidated
        @return debtAdjustment Adjustment amount on liquidated owed.
                * The amount of debt reduced is exactly `debtLiquidated`
                * The adjustment is applied to the amount of tokens burned from the caller's address
                * reverts if `debtLiquidated - debtAdjustment < 0`
     */
    function on_liquidation(
        address caller,
        address market,
        address target,
        uint256 debtLiquidated
    ) external returns (int256 debtAdjustment);

    function on_liquidation_view(
        address caller,
        address market,
        address target,
        uint256 debtLiquidated
    ) external view returns (int256 debtAdjustment);
}
