// Enhanced Dashboard JavaScript - This file is deprecated
// All functionality has been moved inline to dashboard.html for better performance
// and to avoid loading an external JS file for better mobile performance

// Legacy function for backward compatibility (if needed)
function toggleEdit(scanId, show) {
  console.warn('toggleEdit is deprecated. Use startEdit/cancelEdit instead.');
  if (show) {
    startEdit(scanId);
  } else {
    cancelEdit(scanId);
  }
} 