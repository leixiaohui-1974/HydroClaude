.PHONY: help install install-dev test test-cov lint format clean run docker-build docker-up docker-down docs

# 默认目标：显示帮助信息
help:
	@echo "HydroClaude - 可用的Make命令："
	@echo ""
	@echo "  make install        - 安装生产依赖"
	@echo "  make install-dev    - 安装开发依赖"
	@echo "  make test           - 运行所有测试"
	@echo "  make test-cov       - 运行测试并生成覆盖率报告"
	@echo "  make lint           - 代码检查"
	@echo "  make format         - 代码格式化"
	@echo "  make clean          - 清理临时文件"
	@echo "  make run            - 启动应用"
	@echo "  make docker-build   - 构建Docker镜像"
	@echo "  make docker-up      - 启动Docker容器"
	@echo "  make docker-down    - 停止Docker容器"
	@echo "  make docs           - 生成文档"
	@echo ""

# 安装依赖
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-html black pylint mypy

# 运行测试
test:
	pytest tests/backend/ -v

test-cov:
	pytest tests/backend/ -v --cov=solvers --cov=utils --cov-report=html --cov-report=term

# 代码质量
lint:
	pylint solvers/ utils/ --exit-zero
	mypy solvers/ utils/ --ignore-missing-imports

format:
	black solvers/ utils/ tests/

# 清理
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.py~" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/ reports/

# 运行应用
run:
	python main.py

# Docker命令
docker-build:
	docker build -t hydroclaude:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# 文档生成
docs:
	@echo "生成文档..."
	@echo "文档已存在于项目根目录的Markdown文件中"

# 发布到PyPI
build:
	python setup.py sdist bdist_wheel

publish-test:
	twine upload --repository testpypi dist/*

publish:
	twine upload dist/*

# 开发服务器
dev:
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 运行所有检查
check: lint test
	@echo "所有检查通过！"

# 准备发布
release: clean format lint test build
	@echo "准备发布！"
	@echo "运行: make publish-test 或 make publish"
