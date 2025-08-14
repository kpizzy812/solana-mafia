/**
 * Utility functions for formatting
 */

// Smart balance formatting (same as Header and Modal)
export const formatBalance = (balance: number): string => {
  if (balance < 0.00001) {
    return balance.toFixed(9);
  } else if (balance < 0.0001) {
    return balance.toFixed(8);
  } else if (balance < 0.001) {
    return balance.toFixed(7);
  } else if (balance < 0.01) {
    return balance.toFixed(5);
  } else if (balance < 0.1) {
    return balance.toFixed(4);
  } else {
    return balance.toFixed(3);
  }
};

// Format total earnings: 3 decimal places, 0 if zero
export const formatTotalEarnings = (balance: number): string => {
  if (balance === 0) {
    return "0";
  }
  return balance.toFixed(3);
};

// Format earnings balance: up to 6 decimal places, 0 if zero
export const formatEarningsBalance = (balance: number): string => {
  if (balance === 0) {
    return "0";
  }
  
  // Remove trailing zeros for up to 6 decimal places
  let formatted = balance.toFixed(6);
  formatted = formatted.replace(/\.?0+$/, '');
  return formatted;
};