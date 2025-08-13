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