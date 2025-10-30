# HydroClaude Case Library Makefile
# 方便快捷地运行案例和测试

.PHONY: help list test run-all run-quick benchmark clean

# Default target: show help
help:
	@echo ""
	@echo "HydroClaude Case Library - Quick Commands"
	@echo "HydroClaude 案例库 - 快捷命令"
	@echo "=========================================="
	@echo ""
	@echo "Available targets / 可用命令:"
	@echo ""
	@echo "  make help          Show this help message / 显示此帮助信息"
	@echo "  make list          List all available cases / 列出所有可用案例"
	@echo "  make test          Run test suite / 运行测试套件"
	@echo "  make run-all       Run all cases (full) / 运行所有案例（完整）"
	@echo "  make run-quick     Run all cases (quick mode) / 运行所有案例（快速模式）"
	@echo "  make run-case-N    Run specific case (N=1-5) / 运行特定案例 (N=1-5)"
	@echo "  make benchmark     Run performance benchmark / 运行性能基准测试"
	@echo "  make clean         Clean output files / 清理输出文件"
	@echo ""
	@echo "Examples / 示例:"
	@echo "  make run-case-1    # Run Case 01: Hydropower Plant"
	@echo "  make run-case-4    # Run Case 04: Urban Drainage"
	@echo "  make run-quick     # Quick run of all cases"
	@echo "  make benchmark     # Performance benchmarking"
	@echo ""

# List all available cases
list:
	@python run_all_cases.py --list

# Run test suite
test:
	@echo "Running test suite..."
	@python test_cases.py

# Run all cases (full mode)
run-all:
	@echo "Running all cases in full mode..."
	@python run_all_cases.py

# Run all cases (quick mode)
run-quick:
	@echo "Running all cases in quick mode..."
	@python run_all_cases.py --quick

# Run individual cases
run-case-1:
	@echo "Running Case 01: Hydropower Plant..."
	@python run_all_cases.py --case 1

run-case-2:
	@echo "Running Case 02: Water Supply Network..."
	@python run_all_cases.py --case 2

run-case-3:
	@echo "Running Case 03: Irrigation Canal..."
	@python run_all_cases.py --case 3

run-case-4:
	@echo "Running Case 04: Urban Drainage..."
	@python run_all_cases.py --case 4

run-case-5:
	@echo "Running Case 05: River Network..."
	@python run_all_cases.py --case 5

# Performance benchmark
benchmark:
	@echo "Running performance benchmark..."
	@echo "This may take several minutes..."
	@python benchmark_performance.py

# Clean output files
clean:
	@echo "Cleaning output files..."
	@find . -name "*.png" -type f -delete
	@find . -name "*.json" -type f -not -path "./benchmark_results/*" -delete
	@find . -name "*.csv" -type f -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned output files"

# Help aliases
h: help
?:  help
