#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试结果分析工具

分析测试报告，生成统计数据和趋势图

Author: HydroClaude Team
Date: 2025-11-15
"""

import json
import warnings
warnings.filterwarnings("ignore")
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import pandas as pd


class TestResultAnalyzer:
    """测试结果分析器"""
    
    def __init__(self, reports_dir: str = None):
        if reports_dir:
            self.reports_dir = Path(reports_dir)
        else:
            self.reports_dir = Path(__file__).parent / "reports"
    
    def load_latest_report(self) -> Dict[str, Any]:
        """加载最新的测试报告"""
        json_files = list(self.reports_dir.glob("test_report_*.json"))
        
        if not json_files:
            print("❌ 未找到测试报告")
            return None
        
        # 按时间排序，取最新的
        latest_file = sorted(json_files, key=lambda x: x.stat().st_mtime)[-1]
        
        print(f"📊 加载报告: {latest_file.name}")
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def analyze_summary(self, report: Dict[str, Any]):
        """分析测试摘要"""
        summary = report["summary"]
        
        print("\n" + "="*60)
        print("📊 测试摘要分析")
        print("="*60)
        
        print(f"\n总测试数: {summary['total']}")
        print(f"通过数量: {summary['passed']} ({summary['pass_rate']})")
        print(f"失败数量: {summary['failed']}")
        print(f"警告数量: {summary['warning']}")
        print(f"错误数量: {summary['error']}")
        
        # 计算成功率
        if summary['total'] > 0:
            success_rate = (summary['passed'] + summary['warning']) / summary['total'] * 100
            print(f"\n成功率（含警告）: {success_rate:.1f}%")
            
            # 评级
            if success_rate >= 95:
                grade = "A (优秀)"
            elif success_rate >= 90:
                grade = "B (良好)"
            elif success_rate >= 80:
                grade = "C (合格)"
            else:
                grade = "D (需改进)"
            
            print(f"评级: {grade}")
    
    def analyze_by_type(self, report: Dict[str, Any]):
        """按测试类型分析"""
        results = report["results"]
        
        print("\n" + "="*60)
        print("📊 按类型统计")
        print("="*60)
        
        # 按类型分组
        type_stats = {}
        for result in results:
            test_type = result["type"]
            if test_type not in type_stats:
                type_stats[test_type] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0
                }
            
            type_stats[test_type]["total"] += 1
            if result["status"] == "passed":
                type_stats[test_type]["passed"] += 1
            elif result["status"] == "failed":
                type_stats[test_type]["failed"] += 1
        
        # 打印统计
        print(f"\n{'类型':<20} {'总数':<8} {'通过':<8} {'失败':<8} {'通过率':<10}")
        print("-" * 60)
        
        for test_type, stats in sorted(type_stats.items()):
            pass_rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
            print(f"{test_type:<20} {stats['total']:<8} {stats['passed']:<8} {stats['failed']:<8} {pass_rate:.1f}%")
    
    def analyze_performance(self, report: Dict[str, Any]):
        """分析性能"""
        results = report["results"]
        
        print("\n" + "="*60)
        print("📊 性能分析")
        print("="*60)
        
        # 计算统计数据
        durations = [r["duration"] for r in results]
        
        if durations:
            avg_duration = sum(durations) / len(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            
            print(f"\n平均耗时: {avg_duration:.2f}秒")
            print(f"最短耗时: {min_duration:.2f}秒")
            print(f"最长耗时: {max_duration:.2f}秒")
            
            # 找出最慢的案例
            print("\n⏱️  最慢的5个案例:")
            sorted_results = sorted(results, key=lambda x: x["duration"], reverse=True)
            for i, result in enumerate(sorted_results[:5], 1):
                print(f"  {i}. {result['name']}: {result['duration']:.2f}秒")
    
    def analyze_failures(self, report: Dict[str, Any]):
        """分析失败案例"""
        results = report["results"]
        
        failed = [r for r in results if r["status"] in ["failed", "error"]]
        
        if not failed:
            print("\n✅ 没有失败案例！")
            return
        
        print("\n" + "="*60)
        print("❌ 失败案例分析")
        print("="*60)
        
        print(f"\n共 {len(failed)} 个失败案例:")
        
        for result in failed:
            print(f"\n案例 #{result['id']}: {result['name']}")
            print(f"  类型: {result['type']}")
            print(f"  状态: {result['status']}")
            
            if result.get("error"):
                print(f"  错误: {result['error']}")
            
            # 显示失败的步骤
            print("  执行步骤:")
            for step in result["steps"]:
                status_icon = "✅" if "✅" in step else "❌"
                print(f"    {status_icon} {step}")
    
    def analyze_verification(self, report: Dict[str, Any]):
        """分析验证结果"""
        results = report["results"]
        
        print("\n" + "="*60)
        print("📊 验证结果分析")
        print("="*60)
        
        # 统计验证项
        verification_stats = {
            "has_charts": 0,
            "has_data_table": 0,
            "has_profile_plot": 0,
            "has_time_series": 0,
            "has_errors": 0
        }
        
        total = len(results)
        
        for result in results:
            verification = result.get("verification", {})
            
            if verification.get("has_charts"):
                verification_stats["has_charts"] += 1
            if verification.get("has_data_table"):
                verification_stats["has_data_table"] += 1
            if verification.get("has_profile_plot"):
                verification_stats["has_profile_plot"] += 1
            if verification.get("has_time_series"):
                verification_stats["has_time_series"] += 1
            if verification.get("error_messages"):
                verification_stats["has_errors"] += 1
        
        print(f"\n验证项统计 (总计: {total} 个案例):")
        print(f"  图表显示:     {verification_stats['has_charts']}/{total} ({verification_stats['has_charts']/total*100:.1f}%)")
        print(f"  数据表格:     {verification_stats['has_data_table']}/{total} ({verification_stats['has_data_table']/total*100:.1f}%)")
        print(f"  纵剖面图:     {verification_stats['has_profile_plot']}/{total} ({verification_stats['has_profile_plot']/total*100:.1f}%)")
        print(f"  时间序列图:   {verification_stats['has_time_series']}/{total} ({verification_stats['has_time_series']/total*100:.1f}%)")
        print(f"  发现错误:     {verification_stats['has_errors']}/{total}")
    
    def generate_recommendations(self, report: Dict[str, Any]):
        """生成改进建议"""
        summary = report["summary"]
        results = report["results"]
        
        print("\n" + "="*60)
        print("💡 改进建议")
        print("="*60)
        
        recommendations = []
        
        # 检查通过率
        pass_rate = summary["passed"] / summary["total"] * 100 if summary["total"] > 0 else 0
        
        if pass_rate < 90:
            recommendations.append(
                f"⚠️  通过率较低 ({pass_rate:.1f}%)，建议:\n"
                "   - 检查失败案例的共性问题\n"
                "   - 优化测试案例配置\n"
                "   - 改进错误处理"
            )
        
        # 检查性能
        durations = [r["duration"] for r in results]
        if durations:
            avg_duration = sum(durations) / len(durations)
            if avg_duration > 20:
                recommendations.append(
                    f"⚠️  平均耗时较长 ({avg_duration:.1f}秒)，建议:\n"
                    "   - 优化求解器性能\n"
                    "   - 减少网格数量\n"
                    "   - 使用无头模式测试"
                )
        
        # 检查错误
        if summary.get("error", 0) > 0:
            recommendations.append(
                f"⚠️  发现 {summary['error']} 个错误，建议:\n"
                "   - 检查测试环境\n"
                "   - 查看错误日志\n"
                "   - 修复代码Bug"
            )
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"\n{i}. {rec}")
        else:
            print("\n✅ 测试表现优秀，无改进建议！")
    
    def export_to_csv(self, report: Dict[str, Any]):
        """导出为CSV"""
        results = report["results"]
        
        # 准备数据
        data = []
        for result in results:
            data.append({
                "案例ID": result["id"],
                "案例名称": result["name"],
                "测试类型": result["type"],
                "状态": result["status"],
                "耗时(秒)": result["duration"],
                "有图表": result.get("verification", {}).get("has_charts", False),
                "有数据表": result.get("verification", {}).get("has_data_table", False),
                "错误": result.get("error", "")
            })
        
        df = pd.DataFrame(data)
        
        # 保存
        csv_file = self.reports_dir / f"test_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        print(f"\n💾 CSV报告已保存: {csv_file}")
    
    def run(self):
        """执行分析"""
        print("="*60)
        print("📊 HydroClaude 测试结果分析")
        print("="*60)
        
        # 加载报告
        report = self.load_latest_report()
        if not report:
            return
        
        # 各项分析
        self.analyze_summary(report)
        self.analyze_by_type(report)
        self.analyze_performance(report)
        self.analyze_verification(report)
        self.analyze_failures(report)
        self.generate_recommendations(report)
        
        # 导出CSV
        try:
            self.export_to_csv(report)
        except Exception as e:
            print(f"\n⚠️  导出CSV失败: {e}")
        
        print("\n" + "="*60)
        print("✅ 分析完成")
        print("="*60)


def main():
    """主函数"""
    analyzer = TestResultAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()
