#!/bin/bash
# Example 01: Canal Flow - Run All Examples
#
# This script runs all example scripts in sequence and generates
# a comprehensive report.
#
# Usage: bash run_all_examples.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Output directories
OUTPUT_DIR="$SCRIPT_DIR/outputs"
FIGURES_DIR="$OUTPUT_DIR/figures"
ANIMATIONS_DIR="$OUTPUT_DIR/animations"
REPORTS_DIR="$OUTPUT_DIR/reports"

# Create output directories
mkdir -p "$FIGURES_DIR"
mkdir -p "$ANIMATIONS_DIR"
mkdir -p "$REPORTS_DIR"

# Log file
LOG_FILE="$REPORTS_DIR/execution_log.txt"
REPORT_FILE="$REPORTS_DIR/EXECUTION_SUMMARY.md"

# Initialize log
echo "Example 01: Canal Flow - Execution Log" > "$LOG_FILE"
echo "Started: $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Function to run a script
run_script() {
    local script=$1
    local description=$2

    echo ""
    echo "================================================================================"
    echo -e "${BLUE}Running: $description${NC}"
    echo "================================================================================"
    echo "Script: $script"
    echo "--------------------------------------------------------------------------------"

    echo "" >> "$LOG_FILE"
    echo "Running: $description" >> "$LOG_FILE"
    echo "Script: $script" >> "$LOG_FILE"

    local start_time=$(date +%s)

    if python "$script" >> "$LOG_FILE" 2>&1; then
        local end_time=$(date +%s)
        local elapsed=$((end_time - start_time))
        echo -e "${GREEN}✓ SUCCESS${NC} - Completed in ${elapsed}s"
        echo "Status: SUCCESS (${elapsed}s)" >> "$LOG_FILE"
        return 0
    else
        local end_time=$(date +%s)
        local elapsed=$((end_time - start_time))
        echo -e "${RED}✗ FAILED${NC} - Error after ${elapsed}s"
        echo "Status: FAILED (${elapsed}s)" >> "$LOG_FILE"
        return 1
    fi
}

# Start time
TOTAL_START=$(date +%s)

echo "================================================================================"
echo "EXAMPLE 01: CANAL FLOW - MASTER EXECUTION SCRIPT"
echo "================================================================================"
echo "Started: $(date)"
echo ""

# Track success/failure
SUCCESS_COUNT=0
TOTAL_COUNT=0

# Run core example scripts
echo ""
echo "================================================================================"
echo "PART 1: CORE EXAMPLE SCRIPTS"
echo "================================================================================"

scripts=(
    "code/01_basic.py:01 - Basic Simulation"
    "code/02_methods_comparison.py:02 - Methods Comparison"
    "code/03_idz_identification.py:03 - IDZ Identification"
    "code/04_boundary_conditions.py:04 - Boundary Conditions"
    "code/05_step_response.py:05 - Step Response"
    "code/06_animation.py:06 - Animation Generation"
)

for item in "${scripts[@]}"; do
    IFS=":" read -r script description <<< "$item"
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    if run_script "$script" "$description"; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    fi
done

# Run selected test scripts
echo ""
echo "================================================================================"
echo "PART 2: ADVANCED TEST SCRIPTS (Selected)"
echo "================================================================================"

test_scripts=(
    "tests/test_convergence_visual.py:Test - Convergence Visualization"
    "tests/test_performance_comparison.py:Test - Performance Comparison"
)

for item in "${test_scripts[@]}"; do
    IFS=":" read -r script description <<< "$item"
    if [ -f "$script" ]; then
        TOTAL_COUNT=$((TOTAL_COUNT + 1))
        if run_script "$script" "$description"; then
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        fi
    else
        echo "Skipping $script (not found)"
    fi
done

# Calculate total time
TOTAL_END=$(date +%s)
TOTAL_ELAPSED=$((TOTAL_END - TOTAL_START))

# Move outputs to organized structure
echo ""
echo "================================================================================"
echo "ORGANIZING OUTPUTS"
echo "================================================================================"

# Copy/move figures
if [ -d "figures" ]; then
    echo "Copying figures to $FIGURES_DIR..."
    cp -f figures/*.png "$FIGURES_DIR/" 2>/dev/null || true
    cp -f figures/*.gif "$ANIMATIONS_DIR/" 2>/dev/null || true
fi

# Copy/move outputs
if [ -d "outputs/figures" ]; then
    echo "Copying output figures..."
    cp -f outputs/figures/*.png "$FIGURES_DIR/" 2>/dev/null || true
fi

if [ -d "outputs/animations" ]; then
    echo "Copying animations..."
    cp -f outputs/animations/*.gif "$ANIMATIONS_DIR/" 2>/dev/null || true
fi

# Generate summary report
echo ""
echo "================================================================================"
echo "GENERATING SUMMARY REPORT"
echo "================================================================================"

cat > "$REPORT_FILE" << EOF
# Example 01: Canal Flow - Execution Summary

**Generated:** $(date)

## Summary Statistics

- **Total Scripts:** $TOTAL_COUNT
- **Successful:** $SUCCESS_COUNT
- **Failed:** $((TOTAL_COUNT - SUCCESS_COUNT))
- **Success Rate:** $(echo "scale=1; $SUCCESS_COUNT * 100 / $TOTAL_COUNT" | bc)%
- **Total Time:** ${TOTAL_ELAPSED}s ($(echo "scale=1; $TOTAL_ELAPSED / 60" | bc)min)

## Generated Outputs

### Figures

EOF

# List figures
if [ -d "$FIGURES_DIR" ]; then
    for fig in "$FIGURES_DIR"/*.png; do
        if [ -f "$fig" ]; then
            echo "- \`$(basename "$fig")\`" >> "$REPORT_FILE"
        fi
    done
else
    echo "- No figures generated" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF

### Animations

EOF

# List animations
if [ -d "$ANIMATIONS_DIR" ]; then
    for anim in "$ANIMATIONS_DIR"/*.gif; do
        if [ -f "$anim" ]; then
            size=$(du -h "$anim" | cut -f1)
            echo "- \`$(basename "$anim")\` ($size)" >> "$REPORT_FILE"
        fi
    done
else
    echo "- No animations generated" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF

## Execution Details

For full execution log, see: \`execution_log.txt\`

---

*Generated by run_all_examples.sh*
EOF

# Print final summary
echo ""
echo "================================================================================"
echo "EXECUTION COMPLETE"
echo "================================================================================"
echo ""
echo "Results: $SUCCESS_COUNT/$TOTAL_COUNT scripts completed successfully"
echo "Total time: ${TOTAL_ELAPSED}s ($(echo "scale=1; $TOTAL_ELAPSED / 60" | bc)min)"
echo ""
echo "Outputs:"
echo "  Figures:    $FIGURES_DIR/"
echo "  Animations: $ANIMATIONS_DIR/"
echo "  Reports:    $REPORTS_DIR/"
echo ""
echo "Summary report: $REPORT_FILE"
echo "Full log: $LOG_FILE"
echo ""

if [ $SUCCESS_COUNT -eq $TOTAL_COUNT ]; then
    echo -e "${GREEN}🎉 All scripts completed successfully!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some scripts failed. Check the log for details.${NC}"
    exit 1
fi
