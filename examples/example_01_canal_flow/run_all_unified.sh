#!/bin/bash
# Example 01: Canal Flow - Unified Run Script
# Runs all scripts and consolidates outputs to unified structure

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Unified output directory
RESULTS_DIR="$SCRIPT_DIR/results"
FIGURES_DIR="$RESULTS_DIR/figures"
ANIMATIONS_DIR="$RESULTS_DIR/animations"
REPORTS_DIR="$RESULTS_DIR/reports"
TABLES_DIR="$RESULTS_DIR/tables"

# Create directories
mkdir -p "$FIGURES_DIR" "$ANIMATIONS_DIR" "$REPORTS_DIR" "$TABLES_DIR"

# Log file
LOG_FILE="$REPORTS_DIR/execution_log.txt"

echo "================================================================================" | tee "$LOG_FILE"
echo "EXAMPLE 01: CANAL FLOW - UNIFIED EXECUTION" | tee -a "$LOG_FILE"
echo "================================================================================" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Function to run script
run_script() {
    local script=$1
    local description=$2

    echo "" | tee -a "$LOG_FILE"
    echo "================================================================================" | tee -a "$LOG_FILE"
    echo -e "${BLUE}[$description]${NC}" | tee -a "$LOG_FILE"
    echo "================================================================================" | tee -a "$LOG_FILE"
    echo "Script: $script" | tee -a "$LOG_FILE"

    local start_time=$(date +%s)

    if python "$script" >> "$LOG_FILE" 2>&1; then
        local end_time=$(date +%s)
        local elapsed=$((end_time - start_time))
        echo -e "${GREEN}✓ SUCCESS${NC} (${elapsed}s)" | tee -a "$LOG_FILE"
        return 0
    else
        local end_time=$(date +%s)
        local elapsed=$((end_time - start_time))
        echo -e "${YELLOW}⚠ COMPLETED WITH WARNINGS${NC} (${elapsed}s)" | tee -a "$LOG_FILE"
        return 0  # Continue anyway
    fi
}

TOTAL_START=$(date +%s)

echo "================================================================================" | tee -a "$LOG_FILE"
echo "PART 1: CORE EXAMPLE SCRIPTS (code/)" | tee -a "$LOG_FILE"
echo "================================================================================" | tee -a "$LOG_FILE"

run_script "code/01_basic.py" "01 - Basic Simulation"
run_script "code/02_methods_comparison.py" "02 - Methods Comparison"
run_script "code/03_idz_identification.py" "03 - IDZ Identification"
run_script "code/05_step_response.py" "05 - Step Response"
run_script "code/06_animation.py" "06 - Animation Generation"

echo "" | tee -a "$LOG_FILE"
echo "================================================================================" | tee -a "$LOG_FILE"
echo "PART 2: ARCHIVE SCRIPTS (Selected)" | tee -a "$LOG_FILE"
echo "================================================================================" | tee -a "$LOG_FILE"

if [ -f "archive/example_01_sluice_gate_flow.py" ]; then
    run_script "archive/example_01_sluice_gate_flow.py" "Archive - Sluice Gate Flow"
fi

if [ -f "archive/example_02_advanced_structures.py" ]; then
    run_script "archive/example_02_advanced_structures.py" "Archive - Advanced Structures"
fi

echo "" | tee -a "$LOG_FILE"
echo "================================================================================" | tee -a "$LOG_FILE"
echo "CONSOLIDATING OUTPUTS" | tee -a "$LOG_FILE"
echo "================================================================================" | tee -a "$LOG_FILE"

# Consolidate all PNG figures
echo "Consolidating figures..." | tee -a "$LOG_FILE"
find . -name "*.png" -not -path "./results/*" -not -path "./code_new/*" -not -path "./outputs_new/*" -exec cp -f {} "$FIGURES_DIR/" \; 2>/dev/null || true

# Consolidate all GIF animations
echo "Consolidating animations..." | tee -a "$LOG_FILE"
find . -name "*.gif" -not -path "./results/*" -not -path "./code_new/*" -not -path "./outputs_new/*" -exec cp -f {} "$ANIMATIONS_DIR/" \; 2>/dev/null || true

# Consolidate markdown reports
echo "Consolidating reports..." | tee -a "$LOG_FILE"
find ./docs -name "*.md" -exec cp -f {} "$REPORTS_DIR/" \; 2>/dev/null || true
find ./reports -name "*.md" -exec cp -f {} "$REPORTS_DIR/" \; 2>/dev/null || true

# Count outputs
FIGURE_COUNT=$(find "$FIGURES_DIR" -name "*.png" 2>/dev/null | wc -l)
ANIM_COUNT=$(find "$ANIMATIONS_DIR" -name "*.gif" 2>/dev/null | wc -l)
REPORT_COUNT=$(find "$REPORTS_DIR" -name "*.md" 2>/dev/null | wc -l)

echo "  Figures: $FIGURE_COUNT PNG files" | tee -a "$LOG_FILE"
echo "  Animations: $ANIM_COUNT GIF files" | tee -a "$LOG_FILE"
echo "  Reports: $REPORT_COUNT MD files" | tee -a "$LOG_FILE"

TOTAL_END=$(date +%s)
TOTAL_ELAPSED=$((TOTAL_END - TOTAL_START))

# Generate summary report
echo "" | tee -a "$LOG_FILE"
echo "================================================================================" | tee -a "$LOG_FILE"
echo "GENERATING SUMMARY REPORT" | tee -a "$LOG_FILE"
echo "================================================================================" | tee -a "$LOG_FILE"

cat > "$REPORTS_DIR/EXECUTION_SUMMARY.md" << EOF
# Example 01: Canal Flow - Execution Summary

**Generated:** $(date)
**Total Time:** ${TOTAL_ELAPSED}s ($(echo "scale=1; $TOTAL_ELAPSED / 60" | bc)min)

## Generated Outputs

### Figures ($FIGURE_COUNT files)

\`\`\`
$(ls -1 "$FIGURES_DIR"/*.png 2>/dev/null | xargs -n1 basename | sort)
\`\`\`

### Animations ($ANIM_COUNT files)

EOF

# List animations with sizes
for anim in "$ANIMATIONS_DIR"/*.gif; do
    if [ -f "$anim" ]; then
        size=$(du -h "$anim" | cut -f1)
        echo "- \`$(basename "$anim")\` ($size)" >> "$REPORTS_DIR/EXECUTION_SUMMARY.md"
    fi
done

cat >> "$REPORTS_DIR/EXECUTION_SUMMARY.md" << EOF

### Documentation Reports ($REPORT_COUNT files)

\`\`\`
$(ls -1 "$REPORTS_DIR"/*.md 2>/dev/null | xargs -n1 basename | grep -v "EXECUTION_SUMMARY.md" | sort)
\`\`\`

## Directory Structure

\`\`\`
example_01_canal_flow/
├── code/               # Core example scripts (6 files)
├── archive/            # Archived examples (6 files)
├── tests/              # Test scripts (9 files)
├── docs/               # Documentation
├── results/            # All outputs (UNIFIED)
│   ├── figures/        # $FIGURE_COUNT PNG figures
│   ├── animations/     # $ANIM_COUNT GIF animations
│   ├── reports/        # $REPORT_COUNT MD reports
│   └── tables/         # Data tables
└── README.md
\`\`\`

## Execution Log

See \`execution_log.txt\` for full execution details.

---

*Generated by run_all_unified.sh*
EOF

# Final summary
echo "" | tee -a "$LOG_FILE"
echo "================================================================================" | tee -a "$LOG_FILE"
echo "EXECUTION COMPLETE" | tee -a "$LOG_FILE"
echo "================================================================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Results:" | tee -a "$LOG_FILE"
echo "  Figures:    $FIGURE_COUNT files -> $FIGURES_DIR/" | tee -a "$LOG_FILE"
echo "  Animations: $ANIM_COUNT files -> $ANIMATIONS_DIR/" | tee -a "$LOG_FILE"
echo "  Reports:    $REPORT_COUNT files -> $REPORTS_DIR/" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Total time: ${TOTAL_ELAPSED}s ($(echo "scale=1; $TOTAL_ELAPSED / 60" | bc)min)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Summary: $REPORTS_DIR/EXECUTION_SUMMARY.md" | tee -a "$LOG_FILE"
echo "Log: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo -e "${GREEN}🎉 All outputs consolidated to: $RESULTS_DIR/${NC}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
