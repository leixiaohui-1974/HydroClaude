"""
HydroClaude UI HTML分析对标测试

通过分析前端源代码和HTML结构进行UI评估
不依赖浏览器自动化

Author: HydroClaude Test Team
Date: 2025-11-25
"""

import json
import os
import re
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from bs4 import BeautifulSoup

# 报告目录
REPORT_DIR = Path(__file__).parent.parent.parent / "reports" / "html_benchmark"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# 源代码目录
FRONTEND_SRC = Path(__file__).parent.parent.parent / "web" / "frontend" / "src"

# URL配置
FRONTEND_URL = "http://localhost:5173"


class HTMLUIBenchmark:
    """基于HTML和源代码分析的UI对标评估"""

    def __init__(self):
        self.results = {
            "test_date": datetime.now().isoformat(),
            "frontend_url": FRONTEND_URL,
            "source_analysis": {},
            "html_analysis": {},
            "feature_scores": {},
            "overall_score": 0
        }

    def analyze_frontend_source(self) -> Dict:
        """分析前端源代码结构"""
        print("\n" + "="*60)
        print("前端源代码分析")
        print("="*60)

        analysis = {
            "pages": [],
            "components": [],
            "features": [],
            "hooks": [],
            "apis": []
        }

        # 分析页面
        pages_dir = FRONTEND_SRC / "pages"
        if pages_dir.exists():
            for f in pages_dir.glob("*.tsx"):
                page_name = f.stem
                content = f.read_text(encoding='utf-8')

                # 分析页面内容
                page_info = {
                    "name": page_name,
                    "file": str(f),
                    "lines": len(content.split('\n')),
                    "has_state": "useState" in content,
                    "has_effects": "useEffect" in content,
                    "has_routing": "useNavigate" in content or "useParams" in content,
                    "has_forms": "form" in content.lower() or "input" in content.lower(),
                    "has_charts": "Chart" in content or "recharts" in content.lower()
                }
                analysis["pages"].append(page_info)
                print(f"  📄 页面: {page_name} ({page_info['lines']} 行)")

        # 分析组件
        components_dir = FRONTEND_SRC / "components"
        if components_dir.exists():
            for f in components_dir.rglob("*.tsx"):
                comp_name = f.stem
                analysis["components"].append({
                    "name": comp_name,
                    "file": str(f.relative_to(FRONTEND_SRC))
                })

        print(f"\n  组件数量: {len(analysis['components'])}")

        # 分析功能模块
        features_dir = FRONTEND_SRC / "features"
        if features_dir.exists():
            for feature_folder in features_dir.iterdir():
                if feature_folder.is_dir():
                    tsx_files = list(feature_folder.rglob("*.tsx"))
                    analysis["features"].append({
                        "name": feature_folder.name,
                        "files": len(tsx_files)
                    })
                    print(f"  🔧 功能模块: {feature_folder.name} ({len(tsx_files)} 文件)")

        self.results["source_analysis"] = analysis
        return analysis

    def fetch_and_analyze_html(self) -> Dict:
        """获取并分析HTML"""
        print("\n" + "="*60)
        print("HTML内容分析")
        print("="*60)

        analysis = {}

        try:
            response = httpx.get(FRONTEND_URL, timeout=10.0)
            if response.status_code == 200:
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')

                analysis["index"] = {
                    "title": soup.title.string if soup.title else None,
                    "meta_tags": len(soup.find_all('meta')),
                    "scripts": len(soup.find_all('script')),
                    "stylesheets": len(soup.find_all('link', rel='stylesheet')),
                    "has_root": soup.find(id='root') is not None,
                    "has_viewport": soup.find('meta', attrs={'name': 'viewport'}) is not None,
                    "charset": soup.find('meta', charset=True) is not None
                }

                print(f"  标题: {analysis['index']['title']}")
                print(f"  Meta标签: {analysis['index']['meta_tags']}")
                print(f"  脚本: {analysis['index']['scripts']}")
                print(f"  Root元素: {'✅' if analysis['index']['has_root'] else '❌'}")
                print(f"  视口设置: {'✅' if analysis['index']['has_viewport'] else '❌'}")

        except Exception as e:
            print(f"  ❌ 获取HTML失败: {e}")
            analysis["error"] = str(e)

        self.results["html_analysis"] = analysis
        return analysis

    def analyze_ui_features(self) -> Dict:
        """分析UI功能特性"""
        print("\n" + "="*60)
        print("UI功能特性分析")
        print("="*60)

        features = {
            "navigation": self._check_navigation_features(),
            "modeling": self._check_modeling_features(),
            "simulation": self._check_simulation_features(),
            "visualization": self._check_visualization_features(),
            "reports": self._check_report_features(),
            "data_management": self._check_data_features(),
            "user_experience": self._check_ux_features()
        }

        self.results["feature_scores"] = features
        return features

    def _check_navigation_features(self) -> Dict:
        """检查导航功能"""
        print("\n📍 导航功能:")

        score = 0
        max_score = 6
        details = {}

        # 检查侧边栏
        sidebar_file = FRONTEND_SRC / "components" / "layout" / "AppSidebar.tsx"
        if sidebar_file.exists():
            content = sidebar_file.read_text()
            details["sidebar"] = {
                "exists": True,
                "has_links": "href" in content or "Link" in content,
                "has_icons": "Icon" in content or "icon" in content.lower()
            }
            score += 1
            print(f"  ✅ 侧边栏: 存在 (带{'图标' if details['sidebar']['has_icons'] else '无图标'})")
        else:
            details["sidebar"] = {"exists": False}
            print(f"  ❌ 侧边栏: 缺失")

        # 检查头部
        header_file = FRONTEND_SRC / "components" / "layout" / "AppHeader.tsx"
        if header_file.exists():
            details["header"] = {"exists": True}
            score += 1
            print(f"  ✅ 页面头部: 存在")
        else:
            details["header"] = {"exists": False}
            print(f"  ❌ 页面头部: 缺失")

        # 检查快捷操作
        quick_actions = FRONTEND_SRC / "components" / "QuickActionsToolbar.tsx"
        if quick_actions.exists():
            details["quick_actions"] = {"exists": True}
            score += 1
            print(f"  ✅ 快捷操作: 存在")
        else:
            details["quick_actions"] = {"exists": False}
            print(f"  ❌ 快捷操作: 缺失")

        # 检查路由配置
        app_file = FRONTEND_SRC / "App.tsx"
        if app_file.exists():
            content = app_file.read_text()
            has_router = "Router" in content or "Route" in content
            details["routing"] = {"exists": has_router}
            if has_router:
                score += 1
                print(f"  ✅ 路由配置: 存在")
            else:
                print(f"  ❌ 路由配置: 缺失")

        # 检查响应式布局
        has_responsive = False
        for f in FRONTEND_SRC.rglob("*.tsx"):
            content = f.read_text()
            if "md:" in content or "lg:" in content or "@media" in content or "useMediaQuery" in content:
                has_responsive = True
                break
        details["responsive"] = {"exists": has_responsive}
        if has_responsive:
            score += 1
            print(f"  ✅ 响应式设计: 存在")
        else:
            print(f"  ⚠️ 响应式设计: 未检测到")

        # 检查国际化
        has_i18n = (FRONTEND_SRC / "i18n").exists() or any("i18n" in str(f) for f in FRONTEND_SRC.rglob("*.ts"))
        details["i18n"] = {"exists": has_i18n}
        if has_i18n:
            score += 1
            print(f"  ✅ 国际化支持: 存在")
        else:
            print(f"  ⚠️ 国际化支持: 缺失")

        return {
            "score": score,
            "max_score": max_score,
            "percentage": (score / max_score) * 100,
            "details": details
        }

    def _check_modeling_features(self) -> Dict:
        """检查建模功能"""
        print("\n🔧 建模功能:")

        score = 0
        max_score = 6
        details = {}

        modeling_dir = FRONTEND_SRC / "features" / "modeling"

        # 组件面板
        palette = modeling_dir / "components" / "ComponentPalette.tsx"
        if palette.exists():
            details["component_palette"] = {"exists": True}
            score += 1
            print(f"  ✅ 组件面板: 存在")
        else:
            details["component_palette"] = {"exists": False}
            print(f"  ❌ 组件面板: 缺失")

        # 建模画布
        canvas = modeling_dir / "components" / "ModelCanvas.tsx"
        if canvas.exists():
            details["canvas"] = {"exists": True}
            score += 1
            print(f"  ✅ 建模画布: 存在")
        else:
            details["canvas"] = {"exists": False}
            print(f"  ❌ 建模画布: 缺失")

        # 属性面板
        property_panel = modeling_dir / "components" / "PropertyPanel.tsx"
        if property_panel.exists():
            details["property_panel"] = {"exists": True}
            score += 1
            print(f"  ✅ 属性面板: 存在")
        else:
            details["property_panel"] = {"exists": False}
            print(f"  ❌ 属性面板: 缺失")

        # 结构编辑器
        editors = ["GateEditor.tsx", "WeirEditor.tsx", "PumpStationEditor.tsx", "TurbineEditor.tsx"]
        editor_count = sum(1 for e in editors if (modeling_dir / "components" / e).exists())
        details["structure_editors"] = {"count": editor_count, "total": len(editors)}
        if editor_count >= 2:
            score += 1
            print(f"  ✅ 结构编辑器: {editor_count}/{len(editors)} 个")
        else:
            print(f"  ❌ 结构编辑器: 只有 {editor_count}/{len(editors)} 个")

        # 模型库
        model_lib = modeling_dir / "components" / "ModelLibrary.tsx"
        if model_lib.exists():
            details["model_library"] = {"exists": True}
            score += 1
            print(f"  ✅ 模型库: 存在")
        else:
            details["model_library"] = {"exists": False}
            print(f"  ❌ 模型库: 缺失")

        # 模板库
        template_gallery = modeling_dir / "components" / "TemplateGallery.tsx"
        if template_gallery.exists():
            details["template_gallery"] = {"exists": True}
            score += 1
            print(f"  ✅ 模板库: 存在")
        else:
            details["template_gallery"] = {"exists": False}
            print(f"  ❌ 模板库: 缺失")

        return {
            "score": score,
            "max_score": max_score,
            "percentage": (score / max_score) * 100,
            "details": details
        }

    def _check_simulation_features(self) -> Dict:
        """检查仿真功能"""
        print("\n⚙️ 仿真功能:")

        score = 0
        max_score = 6
        details = {}

        sim_dir = FRONTEND_SRC / "features" / "simulation"

        # 配置表单
        config_form = sim_dir / "SimulationConfigForm.tsx"
        if config_form.exists():
            details["config_form"] = {"exists": True}
            score += 1
            print(f"  ✅ 配置表单: 存在")
        else:
            details["config_form"] = {"exists": False}
            print(f"  ❌ 配置表单: 缺失")

        # 仿真工作区
        workspace = sim_dir / "SimulationWorkspace.tsx"
        if workspace.exists():
            details["workspace"] = {"exists": True}
            score += 1
            print(f"  ✅ 仿真工作区: 存在")
        else:
            details["workspace"] = {"exists": False}
            print(f"  ❌ 仿真工作区: 缺失")

        # 结果显示
        results = sim_dir / "SimulationResults.tsx"
        if results.exists():
            details["results"] = {"exists": True}
            score += 1
            print(f"  ✅ 结果显示: 存在")
        else:
            details["results"] = {"exists": False}
            print(f"  ❌ 结果显示: 缺失")

        # 动画控制器
        animation = sim_dir / "components" / "AnimationController.tsx"
        if animation.exists():
            details["animation"] = {"exists": True}
            score += 1
            print(f"  ✅ 动画控制: 存在")
        else:
            details["animation"] = {"exists": False}
            print(f"  ❌ 动画控制: 缺失")

        # 场景管理
        scenarios = sim_dir / "components" / "ScenarioManager.tsx"
        if scenarios.exists():
            details["scenarios"] = {"exists": True}
            score += 1
            print(f"  ✅ 场景管理: 存在")
        else:
            details["scenarios"] = {"exists": False}
            print(f"  ❌ 场景管理: 缺失")

        # 批量仿真
        batch = FRONTEND_SRC / "features" / "batch" / "BatchManager.tsx"
        if batch.exists():
            details["batch"] = {"exists": True}
            score += 1
            print(f"  ✅ 批量仿真: 存在")
        else:
            details["batch"] = {"exists": False}
            print(f"  ❌ 批量仿真: 缺失")

        return {
            "score": score,
            "max_score": max_score,
            "percentage": (score / max_score) * 100,
            "details": details
        }

    def _check_visualization_features(self) -> Dict:
        """检查可视化功能"""
        print("\n📊 可视化功能:")

        score = 0
        max_score = 6
        details = {}

        sim_comp = FRONTEND_SRC / "features" / "simulation" / "components"

        # 增强图表
        charts = sim_comp / "EnhancedCharts.tsx"
        if charts.exists():
            details["enhanced_charts"] = {"exists": True}
            score += 1
            print(f"  ✅ 增强图表: 存在")
        else:
            # 检查其他位置
            alt_charts = FRONTEND_SRC / "components" / "visualization" / "EnhancedCharts.tsx"
            if alt_charts.exists():
                details["enhanced_charts"] = {"exists": True}
                score += 1
                print(f"  ✅ 增强图表: 存在")
            else:
                details["enhanced_charts"] = {"exists": False}
                print(f"  ❌ 增强图表: 缺失")

        # 3D可视化
        plot3d = sim_comp / "Plot3D.tsx"
        if plot3d.exists():
            details["plot3d"] = {"exists": True}
            score += 1
            print(f"  ✅ 3D可视化: 存在")
        else:
            details["plot3d"] = {"exists": False}
            print(f"  ❌ 3D可视化: 缺失")

        # 对比视图
        comparison = sim_comp / "ComparisonView.tsx"
        if comparison.exists():
            details["comparison_view"] = {"exists": True}
            score += 1
            print(f"  ✅ 对比视图: 存在")
        else:
            details["comparison_view"] = {"exists": False}
            print(f"  ❌ 对比视图: 缺失")

        # 结果导出
        export = sim_comp / "ResultsExport.tsx"
        if export.exists():
            details["results_export"] = {"exists": True}
            score += 1
            print(f"  ✅ 结果导出: 存在")
        else:
            details["results_export"] = {"exists": False}
            print(f"  ❌ 结果导出: 缺失")

        # 动画控制
        animation = sim_comp / "AnimationController.tsx"
        if animation.exists():
            details["animation_controller"] = {"exists": True}
            score += 1
            print(f"  ✅ 动画控制: 存在")
        else:
            details["animation_controller"] = {"exists": False}
            print(f"  ❌ 动画控制: 缺失")

        # 检查是否使用Recharts或其他图表库
        has_charts_lib = False
        for f in FRONTEND_SRC.rglob("*.tsx"):
            content = f.read_text()
            if "recharts" in content.lower() or "Chart" in content:
                has_charts_lib = True
                break
        details["charts_library"] = {"exists": has_charts_lib}
        if has_charts_lib:
            score += 1
            print(f"  ✅ 图表库: 已集成")
        else:
            print(f"  ❌ 图表库: 未检测到")

        return {
            "score": score,
            "max_score": max_score,
            "percentage": (score / max_score) * 100,
            "details": details
        }

    def _check_report_features(self) -> Dict:
        """检查报告功能"""
        print("\n📝 报告功能:")

        score = 0
        max_score = 4
        details = {}

        # 报告生成器
        report_gen = FRONTEND_SRC / "features" / "reports" / "ReportGenerator.tsx"
        if report_gen.exists():
            details["report_generator"] = {"exists": True}
            score += 1
            print(f"  ✅ 报告生成器: 存在")
        else:
            details["report_generator"] = {"exists": False}
            print(f"  ❌ 报告生成器: 缺失")

        # 结果导出
        results_export = FRONTEND_SRC / "features" / "simulation" / "components" / "ResultsExport.tsx"
        if results_export.exists():
            details["results_export"] = {"exists": True}
            score += 1
            print(f"  ✅ 结果导出: 存在")
        else:
            details["results_export"] = {"exists": False}
            print(f"  ❌ 结果导出: 缺失")

        # 结果分析
        result_analysis = FRONTEND_SRC / "features" / "analysis" / "ResultAnalysis.tsx"
        if result_analysis.exists():
            details["result_analysis"] = {"exists": True}
            score += 1
            print(f"  ✅ 结果分析: 存在")
        else:
            details["result_analysis"] = {"exists": False}
            print(f"  ❌ 结果分析: 缺失")

        # 配置分析
        config_analysis = FRONTEND_SRC / "features" / "analysis" / "ConfigAnalysis.tsx"
        if config_analysis.exists():
            details["config_analysis"] = {"exists": True}
            score += 1
            print(f"  ✅ 配置分析: 存在")
        else:
            details["config_analysis"] = {"exists": False}
            print(f"  ❌ 配置分析: 缺失")

        return {
            "score": score,
            "max_score": max_score,
            "percentage": (score / max_score) * 100,
            "details": details
        }

    def _check_data_features(self) -> Dict:
        """检查数据管理功能"""
        print("\n💾 数据管理功能:")

        score = 0
        max_score = 4
        details = {}

        # 数据导入
        data_importer = FRONTEND_SRC / "features" / "advanced" / "DataImporter.tsx"
        if data_importer.exists():
            details["data_importer"] = {"exists": True}
            score += 1
            print(f"  ✅ 数据导入: 存在")
        else:
            details["data_importer"] = {"exists": False}
            print(f"  ❌ 数据导入: 缺失")

        # 模型IO
        model_io = FRONTEND_SRC / "features" / "modeling" / "components" / "ModelIO.tsx"
        if model_io.exists():
            details["model_io"] = {"exists": True}
            score += 1
            print(f"  ✅ 模型导入导出: 存在")
        else:
            details["model_io"] = {"exists": False}
            print(f"  ❌ 模型导入导出: 缺失")

        # 场景管理
        scenario_mgr = FRONTEND_SRC / "features" / "simulation" / "components" / "ScenarioManager.tsx"
        if scenario_mgr.exists():
            details["scenario_manager"] = {"exists": True}
            score += 1
            print(f"  ✅ 场景管理: 存在")
        else:
            details["scenario_manager"] = {"exists": False}
            print(f"  ❌ 场景管理: 缺失")

        # 测试案例库
        test_cases = FRONTEND_SRC / "features" / "test-cases" / "TestCaseLibrary.tsx"
        if test_cases.exists():
            details["test_case_library"] = {"exists": True}
            score += 1
            print(f"  ✅ 测试案例库: 存在")
        else:
            details["test_case_library"] = {"exists": False}
            print(f"  ❌ 测试案例库: 缺失")

        return {
            "score": score,
            "max_score": max_score,
            "percentage": (score / max_score) * 100,
            "details": details
        }

    def _check_ux_features(self) -> Dict:
        """检查用户体验功能"""
        print("\n✨ 用户体验功能:")

        score = 0
        max_score = 4
        details = {}

        # 错误显示
        error_display = FRONTEND_SRC / "components" / "ErrorDisplay.tsx"
        if error_display.exists():
            details["error_display"] = {"exists": True}
            score += 1
            print(f"  ✅ 错误显示: 存在")
        else:
            details["error_display"] = {"exists": False}
            print(f"  ❌ 错误显示: 缺失")

        # 组件配置表单
        config_form = FRONTEND_SRC / "components" / "ComponentConfigForm.tsx"
        if config_form.exists():
            details["config_form"] = {"exists": True}
            score += 1
            print(f"  ✅ 配置表单: 存在")
        else:
            details["config_form"] = {"exists": False}
            print(f"  ❌ 配置表单: 缺失")

        # 统一组件选择器
        unified_selector = FRONTEND_SRC / "components" / "UnifiedComponentSelector.tsx"
        if unified_selector.exists():
            details["unified_selector"] = {"exists": True}
            score += 1
            print(f"  ✅ 统一组件选择器: 存在")
        else:
            details["unified_selector"] = {"exists": False}
            print(f"  ❌ 统一组件选择器: 缺失")

        # 关于页面
        about_page = FRONTEND_SRC / "pages" / "AboutPage.tsx"
        if about_page.exists():
            details["about_page"] = {"exists": True}
            score += 1
            print(f"  ✅ 关于页面: 存在")
        else:
            details["about_page"] = {"exists": False}
            print(f"  ❌ 关于页面: 缺失")

        return {
            "score": score,
            "max_score": max_score,
            "percentage": (score / max_score) * 100,
            "details": details
        }

    def calculate_overall_score(self) -> float:
        """计算总体评分"""
        weights = {
            "navigation": 0.15,
            "modeling": 0.20,
            "simulation": 0.20,
            "visualization": 0.20,
            "reports": 0.10,
            "data_management": 0.10,
            "user_experience": 0.05
        }

        total_weighted = 0
        for category, data in self.results["feature_scores"].items():
            weight = weights.get(category, 0.1)
            total_weighted += data["percentage"] * weight

        self.results["overall_score"] = total_weighted
        return total_weighted

    def generate_report(self):
        """生成测试报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # JSON报告
        json_file = REPORT_DIR / f"html_benchmark_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n📄 JSON报告: {json_file}")

        # HTML报告
        html_file = REPORT_DIR / f"html_benchmark_{timestamp}.html"
        html_content = self._generate_html_report()
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"📄 HTML报告: {html_file}")

        return json_file, html_file

    def _generate_html_report(self) -> str:
        """生成HTML报告"""
        categories_html = ""
        for cat, data in self.results["feature_scores"].items():
            score_class = "excellent" if data["percentage"] >= 80 else "good" if data["percentage"] >= 60 else "needs-work"
            details_html = ""
            for key, val in data.get("details", {}).items():
                status = "✅" if val.get("exists", False) else "❌"
                details_html += f"<li>{status} {key}</li>"

            categories_html += f"""
            <div class="category-card">
                <h3>{cat}</h3>
                <div class="score-bar">
                    <div class="score-fill {score_class}" style="width: {data['percentage']}%"></div>
                </div>
                <p>{data['score']}/{data['max_score']} ({data['percentage']:.1f}%)</p>
                <ul class="details-list">{details_html}</ul>
            </div>
            """

        overall = self.results.get("overall_score", 0)

        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>HydroClaude UI源代码分析报告</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .card {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .category-card {{ background: #fafafa; border-radius: 8px; padding: 15px; margin: 10px 0; }}
        .score-bar {{ background: #e0e0e0; border-radius: 10px; height: 20px; overflow: hidden; margin: 10px 0; }}
        .score-fill {{ height: 100%; border-radius: 10px; }}
        .excellent {{ background: #4caf50; }}
        .good {{ background: #8bc34a; }}
        .needs-work {{ background: #ff9800; }}
        .details-list {{ list-style: none; padding: 0; margin-top: 10px; font-size: 14px; }}
        .details-list li {{ padding: 3px 0; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .summary-item {{ background: white; padding: 15px; border-radius: 8px; text-align: center; }}
        .summary-item .value {{ font-size: 24px; font-weight: bold; color: #667eea; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>HydroClaude UI 源代码分析报告</h1>
        <p>测试日期: {self.results['test_date']}</p>
        <p>综合评分: <strong>{overall:.1f}%</strong></p>
    </div>

    <div class="card">
        <h2>综合评分</h2>
        <div class="score-bar">
            <div class="score-fill {'excellent' if overall >= 80 else 'good' if overall >= 60 else 'needs-work'}" style="width: {overall}%"></div>
        </div>
        <p>{overall:.1f}% - {'优秀' if overall >= 80 else '良好' if overall >= 60 else '需改进'}</p>
    </div>

    <div class="card">
        <h2>源代码统计</h2>
        <div class="summary">
            <div class="summary-item">
                <div class="value">{len(self.results['source_analysis'].get('pages', []))}</div>
                <div>页面</div>
            </div>
            <div class="summary-item">
                <div class="value">{len(self.results['source_analysis'].get('components', []))}</div>
                <div>组件</div>
            </div>
            <div class="summary-item">
                <div class="value">{len(self.results['source_analysis'].get('features', []))}</div>
                <div>功能模块</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>功能评估详情</h2>
        {categories_html}
    </div>

    <div class="card">
        <h2>商业软件对标</h2>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background: #f5f5f5;">
                <th style="padding: 10px; text-align: left;">商业软件</th>
                <th style="padding: 10px;">达标阈值</th>
                <th style="padding: 10px;">实际得分</th>
                <th style="padding: 10px;">状态</th>
            </tr>
            <tr><td style="padding: 10px;">HEC-RAS</td><td style="padding: 10px; text-align: center;">50%</td><td style="padding: 10px; text-align: center;">{overall:.1f}%</td><td style="padding: 10px; text-align: center;">{'✅ 达标' if overall >= 50 else '❌ 未达标'}</td></tr>
            <tr><td style="padding: 10px;">MIKE 11</td><td style="padding: 10px; text-align: center;">55%</td><td style="padding: 10px; text-align: center;">{overall:.1f}%</td><td style="padding: 10px; text-align: center;">{'✅ 达标' if overall >= 55 else '❌ 未达标'}</td></tr>
            <tr><td style="padding: 10px;">EPANET</td><td style="padding: 10px; text-align: center;">45%</td><td style="padding: 10px; text-align: center;">{overall:.1f}%</td><td style="padding: 10px; text-align: center;">{'✅ 达标' if overall >= 45 else '❌ 未达标'}</td></tr>
            <tr><td style="padding: 10px;">HAMMER</td><td style="padding: 10px; text-align: center;">45%</td><td style="padding: 10px; text-align: center;">{overall:.1f}%</td><td style="padding: 10px; text-align: center;">{'✅ 达标' if overall >= 45 else '❌ 未达标'}</td></tr>
        </table>
    </div>
</body>
</html>
"""

    def run(self):
        """运行完整测试"""
        print("\n" + "="*70)
        print("HydroClaude UI 源代码分析对标测试")
        print("="*70)

        # 分析源代码
        self.analyze_frontend_source()

        # 分析HTML
        self.fetch_and_analyze_html()

        # 分析UI功能
        self.analyze_ui_features()

        # 计算总分
        overall = self.calculate_overall_score()

        # 生成报告
        self.generate_report()

        # 打印总结
        print("\n" + "="*70)
        print("测试总结")
        print("="*70)

        for cat, data in self.results["feature_scores"].items():
            bar = "█" * int(data["percentage"] / 10) + "░" * (10 - int(data["percentage"] / 10))
            print(f"  {cat:20} [{bar}] {data['percentage']:5.1f}%")

        print("-" * 50)
        overall_bar = "█" * int(overall / 10) + "░" * (10 - int(overall / 10))
        print(f"  {'综合评分':20} [{overall_bar}] {overall:5.1f}%")

        # 商业软件对标
        print("\n商业软件对标:")
        thresholds = {"HEC-RAS": 50, "MIKE 11": 55, "EPANET": 45, "HAMMER": 45}
        for software, threshold in thresholds.items():
            status = "✅ 达标" if overall >= threshold else "❌ 未达标"
            print(f"  vs {software}: {status} (阈值: {threshold}%, 实际: {overall:.1f}%)")

        return self.results


if __name__ == "__main__":
    benchmark = HTMLUIBenchmark()
    benchmark.run()
