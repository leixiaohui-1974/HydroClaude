/**
 * HydroClaude 统一结果查看器
 * Universal Results Viewer
 * 
 * 核心特点：
 * 1. 自动适配所有场景（稳态/非恒定流/有无结构）
 * 2. 组件化设计
 * 3. 交互式图表
 * 4. 响应式布局
 * 
 * @version 1.0.0
 * @author HydroClaude Development Team
 * @date 2025-11-15
 */

class HydroViewer {
    constructor(resultData) {
        this.data = resultData;
        this.currentTime = 0;
        this.selectedLocations = [];
        this.charts = {};
        
        // 场景检测
        this.isSteady = resultData.simulation.type === 'steady';
        this.hasStructures = resultData.structures && resultData.structures.length > 0;
        this.hasTemporalData = resultData.geometry.dimensions.temporal.count > 1;
        
        console.log('HydroViewer initialized', {
            steady: this.isSteady,
            structures: this.hasStructures,
            temporal: this.hasTemporalData
        });
    }
    
    /**
     * 初始化查看器
     */
    async init() {
        console.log('Initializing HydroViewer...');
        
        try {
            // 1. 填充基本信息
            this.fillMetadata();
            
            // 2. 初始化UI组件
            this.setupUI();
            
            // 3. 渲染总览
            this.renderOverview();
            
            // 4. 渲染空间视图
            this.renderSpatialView();
            
            // 5. 渲染时间视图（如果适用）
            if (this.hasTemporalData) {
                this.renderTemporalView();
            } else {
                document.getElementById('temporal-section').style.display = 'none';
            }
            
            // 6. 渲染结构分析（如果有）
            if (this.hasStructures) {
                this.renderStructures();
            } else {
                document.getElementById('structures-section').style.display = 'none';
            }
            
            // 7. 渲染验证报告
            this.renderValidation();
            
            // 8. 设置导出功能
            this.setupExport();
            
            console.log('HydroViewer initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize HydroViewer:', error);
            this.showError('初始化失败: ' + error.message);
        }
    }
    
    /**
     * 填充元数据
     */
    fillMetadata() {
        const meta = this.data.metadata;
        const sim = this.data.simulation;
        
        document.getElementById('sim-title').textContent = meta.title || '未命名仿真';
        document.getElementById('sim-type').textContent = 
            sim.type === 'steady' ? '稳态流动' : '非恒定流';
        document.getElementById('sim-status').textContent = sim.status || 'unknown';
        document.getElementById('sim-status').className = 
            'badge ' + (sim.status === 'completed' ? 'badge-success' : 'badge-warning');
        
        if (sim.duration_seconds !== undefined) {
            document.getElementById('compute-time').textContent = 
                `${sim.duration_seconds.toFixed(2)}秒`;
        }
        
        if (sim.convergence) {
            const conv = sim.convergence;
            document.getElementById('convergence-status').textContent = 
                conv.converged ? 
                `✅ 已收敛 (${conv.iterations}次迭代)` : 
                '❌ 未收敛';
        }
        
        if (this.data.validation && this.data.validation.overall_score !== undefined) {
            document.getElementById('validation-score').textContent = 
                `${this.data.validation.overall_score.toFixed(1)} (${this.data.validation.overall_grade || 'N/A'})`;
        }
    }
    
    /**
     * 设置UI组件
     */
    setupUI() {
        // 时间滑块（非恒定流）
        if (this.hasTemporalData) {
            const timeSlider = document.getElementById('time-slider');
            const timeDisplay = document.getElementById('time-display');
            const times = this.data.geometry.dimensions.temporal.values;
            
            timeSlider.min = 0;
            timeSlider.max = times.length - 1;
            timeSlider.value = times.length - 1; // 默认最后时刻
            
            timeSlider.addEventListener('input', (e) => {
                const idx = parseInt(e.target.value);
                this.currentTime = idx;
                timeDisplay.textContent = `t = ${times[idx].toFixed(1)}s`;
                this.updateSpatialPlots(idx);
            });
            
            timeDisplay.textContent = `t = ${times[times.length - 1].toFixed(1)}s`;
        }
        
        // 变量选择按钮
        const varButtons = document.querySelectorAll('[data-var]');
        varButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                varButtons.forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                const variable = e.target.dataset.var;
                this.plotSpatialDistribution(variable);
            });
        });
        
        // 位置选择器（非恒定流）
        if (this.hasTemporalData) {
            const locSelector = document.getElementById('location-selector');
            const x = this.data.geometry.dimensions.spatial.values;
            
            // 添加几个关键位置
            const indices = [0, Math.floor(x.length / 2), x.length - 1];
            const names = ['上游', '中游', '下游'];
            
            indices.forEach((idx, i) => {
                const option = document.createElement('option');
                option.value = idx;
                option.text = `${names[i]} (x=${x[idx].toFixed(0)}m)`;
                option.selected = true;
                locSelector.appendChild(option);
            });
            
            this.selectedLocations = indices;
            
            locSelector.addEventListener('change', () => {
                this.selectedLocations = Array.from(locSelector.selectedOptions)
                    .map(opt => parseInt(opt.value));
                this.plotTimeSeries();
            });
        }
    }
    
    /**
     * 渲染总览面板
     */
    renderOverview() {
        console.log('Rendering overview...');
        
        // 统计表格
        const statsTable = document.getElementById('stats-table');
        const variables = this.data.variables;
        
        let html = '<thead><tr><th>变量</th><th>最小值</th><th>最大值</th><th>平均值</th><th>标准差</th></tr></thead><tbody>';
        
        for (const [key, variable] of Object.entries(variables)) {
            if (variable.statistics) {
                const stats = variable.statistics;
                html += `<tr>
                    <td><strong>${variable.name}</strong> (${variable.unit})</td>
                    <td>${stats.min.toFixed(4)}</td>
                    <td>${stats.max.toFixed(4)}</td>
                    <td>${stats.mean.toFixed(4)}</td>
                    <td>${stats.std.toFixed(4)}</td>
                </tr>`;
            }
        }
        
        html += '</tbody>';
        statsTable.innerHTML = html;
    }
    
    /**
     * 渲染空间视图
     */
    renderSpatialView() {
        console.log('Rendering spatial view...');
        
        // 纵剖面图
        this.plotLongitudinalProfile();
        
        // 默认显示流量分布
        this.plotSpatialDistribution('flow');
    }
    
    /**
     * 绘制纵剖面图
     */
    plotLongitudinalProfile() {
        const x = this.data.geometry.dimensions.spatial.values;
        const h_data = this.data.variables.depth.data;
        
        // 取最后时刻（或唯一时刻）
        const timeIdx = h_data.length - 1;
        const h = h_data[timeIdx];
        
        // 获取床面高程
        let z_bed;
        if (this.data.geometry.properties.bed_elevation) {
            z_bed = this.data.geometry.properties.bed_elevation;
        } else {
            // 简单估算
            const length = this.data.geometry.properties.length;
            const slope = this.data.geometry.properties.slope;
            z_bed = x.map(xi => (length - xi) * slope);
        }
        
        const z_surface = h.map((hi, i) => z_bed[i] + hi);
        
        // 使用Plotly绘制
        const traces = [
            {
                x: x,
                y: z_bed,
                fill: 'tozeroy',
                name: '河床',
                type: 'scatter',
                mode: 'lines',
                fillcolor: 'rgba(139, 69, 19, 0.5)',
                line: {color: 'rgb(139, 69, 19)', width: 2}
            },
            {
                x: x,
                y: z_surface,
                fill: 'tonexty',
                name: '水面',
                type: 'scatter',
                mode: 'lines',
                fillcolor: 'rgba(0, 191, 255, 0.5)',
                line: {color: 'rgb(0, 100, 255)', width: 2.5}
            }
        ];
        
        const layout = {
            title: {
                text: '纵剖面图 - Longitudinal Profile',
                font: {size: 16, family: 'Arial, sans-serif'}
            },
            xaxis: {
                title: '距离 (m)',
                gridcolor: 'rgba(200,200,200,0.3)'
            },
            yaxis: {
                title: '高程 (m)',
                gridcolor: 'rgba(200,200,200,0.3)'
            },
            hovermode: 'x unified',
            plot_bgcolor: 'rgba(250,250,250,1)',
            paper_bgcolor: 'white',
            showlegend: true,
            legend: {
                x: 0.02,
                y: 0.98,
                bgcolor: 'rgba(255,255,255,0.8)'
            }
        };
        
        const config = {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['lasso2d', 'select2d']
        };
        
        Plotly.newPlot('plot-longitudinal', traces, layout, config);
        this.charts['longitudinal'] = true;
    }
    
    /**
     * 绘制空间分布图
     */
    plotSpatialDistribution(variable) {
        console.log(`Plotting spatial distribution: ${variable}`);
        
        const x = this.data.geometry.dimensions.spatial.values;
        const varData = this.data.variables[variable];
        
        if (!varData) {
            console.warn(`Variable ${variable} not found`);
            return;
        }
        
        // 取最后时刻（或唯一时刻）
        const timeIdx = varData.data.length - 1;
        const y = varData.data[timeIdx];
        
        const trace = {
            x: x,
            y: y,
            type: 'scatter',
            mode: 'lines+markers',
            name: varData.name,
            line: {color: this.getVariableColor(variable), width: 2.5},
            marker: {size: 4}
        };
        
        const layout = {
            title: {
                text: `${varData.name}空间分布`,
                font: {size: 16}
            },
            xaxis: {
                title: '距离 (m)',
                gridcolor: 'rgba(200,200,200,0.3)'
            },
            yaxis: {
                title: `${varData.name} (${varData.unit})`,
                gridcolor: 'rgba(200,200,200,0.3)'
            },
            hovermode: 'x unified',
            plot_bgcolor: 'rgba(250,250,250,1)',
            paper_bgcolor: 'white'
        };
        
        const config = {responsive: true};
        
        Plotly.newPlot('plot-spatial-distribution', [trace], layout, config);
    }
    
    /**
     * 更新空间图（时间变化）
     */
    updateSpatialPlots(timeIdx) {
        // 更新纵剖面
        const h = this.data.variables.depth.data[timeIdx];
        const x = this.data.geometry.dimensions.spatial.values;
        const z_bed = this.data.geometry.properties.bed_elevation || x.map(xi => 0);
        const z_surface = h.map((hi, i) => z_bed[i] + hi);
        
        Plotly.restyle('plot-longitudinal', {
            y: [z_bed, z_surface]
        }, [0, 1]);
        
        // 更新分布图
        const activeVar = document.querySelector('[data-var].active');
        if (activeVar) {
            const variable = activeVar.dataset.var;
            const y = this.data.variables[variable].data[timeIdx];
            Plotly.restyle('plot-spatial-distribution', {y: [y]}, [0]);
        }
    }
    
    /**
     * 渲染时间视图
     */
    renderTemporalView() {
        console.log('Rendering temporal view...');
        
        this.plotTimeSeries();
        this.plotContour();
    }
    
    /**
     * 绘制时间序列
     */
    plotTimeSeries() {
        const t = this.data.geometry.dimensions.temporal.values;
        const x = this.data.geometry.dimensions.spatial.values;
        const h_data = this.data.variables.depth.data;
        const Q_data = this.data.variables.flow.data;
        
        const traces = [];
        const colors = ['rgb(31, 119, 180)', 'rgb(255, 127, 14)', 'rgb(44, 160, 44)'];
        
        this.selectedLocations.forEach((idx, i) => {
            const h_series = h_data.map(h_t => h_t[idx]);
            const Q_series = Q_data.map(Q_t => Q_t[idx]);
            
            traces.push({
                x: t,
                y: h_series,
                name: `水深 @ x=${x[idx].toFixed(0)}m`,
                type: 'scatter',
                mode: 'lines',
                line: {color: colors[i], width: 2},
                yaxis: 'y'
            });
            
            traces.push({
                x: t,
                y: Q_series,
                name: `流量 @ x=${x[idx].toFixed(0)}m`,
                type: 'scatter',
                mode: 'lines',
                line: {color: colors[i], width: 2, dash: 'dash'},
                yaxis: 'y2',
                visible: 'legendonly'
            });
        });
        
        const layout = {
            title: '时间序列 - Time Series',
            xaxis: {
                title: '时间 (s)',
                gridcolor: 'rgba(200,200,200,0.3)'
            },
            yaxis: {
                title: '水深 (m)',
                gridcolor: 'rgba(200,200,200,0.3)'
            },
            yaxis2: {
                title: '流量 (m³/s)',
                overlaying: 'y',
                side: 'right'
            },
            hovermode: 'x unified',
            plot_bgcolor: 'rgba(250,250,250,1)',
            showlegend: true
        };
        
        const config = {responsive: true};
        
        Plotly.newPlot('plot-time-series', traces, layout, config);
    }
    
    /**
     * 绘制时空等值线
     */
    plotContour() {
        const t = this.data.geometry.dimensions.temporal.values;
        const x = this.data.geometry.dimensions.spatial.values;
        const h_data = this.data.variables.depth.data;
        
        const trace = {
            x: x,
            y: t,
            z: h_data,
            type: 'contour',
            colorscale: 'Blues',
            contours: {
                coloring: 'heatmap'
            },
            colorbar: {
                title: '水深 (m)',
                titleside: 'right'
            }
        };
        
        const layout = {
            title: '时空等值线图 - Space-Time Contour',
            xaxis: {title: '距离 (m)'},
            yaxis: {title: '时间 (s)'},
            plot_bgcolor: 'white'
        };
        
        const config = {responsive: true};
        
        Plotly.newPlot('plot-contour', [trace], layout, config);
    }
    
    /**
     * 渲染水工结构
     */
    renderStructures() {
        console.log('Rendering structures...');
        
        const container = document.getElementById('structure-cards');
        const structures = this.data.structures;
        
        let html = '';
        
        structures.forEach((struct, idx) => {
            const results = struct.results;
            
            html += `
                <div class="card mb-3">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">
                            <i class="fas fa-cogs"></i> ${struct.name}
                            <span class="badge badge-light float-right">${struct.type}</span>
                        </h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>位置:</strong> ${struct.position.x.toFixed(1)} m</p>
                                <p><strong>索引:</strong> ${struct.position.index}</p>
                            </div>
                            <div class="col-md-6">
                                ${this.renderStructureParameters(struct)}
                            </div>
                        </div>
                        
                        <hr>
                        
                        <h6>计算结果</h6>
                        <div class="row">
                            <div class="col-md-4">
                                <div class="metric-box">
                                    <div class="metric-label">上游水深</div>
                                    <div class="metric-value">${results.upstream_depth.toFixed(3)} m</div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="metric-box">
                                    <div class="metric-label">下游水深</div>
                                    <div class="metric-value">${results.downstream_depth.toFixed(3)} m</div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="metric-box">
                                    <div class="metric-label">水头损失</div>
                                    <div class="metric-value">${results.head_loss.toFixed(3)} m</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="row mt-2">
                            <div class="col-md-6">
                                <div class="metric-box">
                                    <div class="metric-label">流量</div>
                                    <div class="metric-value">${results.flow.toFixed(3)} m³/s</div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="metric-box">
                                    <div class="metric-label">流速（上→下）</div>
                                    <div class="metric-value">
                                        ${results.velocity_upstream.toFixed(2)} → ${results.velocity_downstream.toFixed(2)} m/s
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    }
    
    /**
     * 渲染结构参数
     */
    renderStructureParameters(struct) {
        const params = struct.parameters;
        let html = '<p><strong>参数:</strong></p><ul class="small">';
        
        for (const [key, value] of Object.entries(params)) {
            if (typeof value === 'number') {
                html += `<li>${key}: ${value.toFixed(3)}</li>`;
            } else {
                html += `<li>${key}: ${value}</li>`;
            }
        }
        
        html += '</ul>';
        return html;
    }
    
    /**
     * 渲染验证报告
     */
    renderValidation() {
        console.log('Rendering validation...');
        
        if (!this.data.validation) {
            document.getElementById('validation-section').innerHTML = 
                '<p class="text-muted">无验证信息</p>';
            return;
        }
        
        const val = this.data.validation;
        
        // 评分雷达图
        if (val.mass_conservation && val.overall_score) {
            this.plotValidationRadar();
        }
        
        // 详细信息
        if (val.mass_conservation) {
            const mc = val.mass_conservation;
            this.updateProgressBar(
                'mass-conservation-bar',
                100 - mc.error_percent,
                mc.grade,
                `${(100 - mc.error_percent).toFixed(2)}% - ${mc.grade}`
            );
        }
        
        if (val.energy_conservation) {
            const ec = val.energy_conservation;
            this.updateProgressBar(
                'energy-conservation-bar',
                100 - ec.error_percent,
                ec.grade,
                `${(100 - ec.error_percent).toFixed(2)}% - ${ec.grade}`
            );
        }
        
        if (val.stability) {
            const stable = val.stability.status === 'Stable';
            this.updateProgressBar(
                'stability-bar',
                stable ? 95 : 50,
                val.stability.status,
                val.stability.status
            );
        }
    }
    
    /**
     * 绘制验证雷达图
     */
    plotValidationRadar() {
        const val = this.data.validation;
        
        const data = [{
            type: 'scatterpolar',
            r: [
                100 - (val.mass_conservation?.error_percent || 0),
                100 - (val.energy_conservation?.error_percent || 50),
                val.stability?.max_froude < 1.0 ? 95 : 70
            ],
            theta: ['质量守恒', '能量守恒', '稳定性'],
            fill: 'toself',
            name: '验证评分',
            line: {color: 'rgb(31, 119, 180)'},
            fillcolor: 'rgba(31, 119, 180, 0.3)'
        }];
        
        const layout = {
            polar: {
                radialaxis: {
                    visible: true,
                    range: [0, 100],
                    tickfont: {size: 10}
                }
            },
            title: '验证评分雷达图',
            showlegend: false
        };
        
        const config = {responsive: true};
        
        Plotly.newPlot('plot-validation-radar', data, layout, config);
    }
    
    /**
     * 更新进度条
     */
    updateProgressBar(id, value, grade, text) {
        const bar = document.getElementById(id);
        if (!bar) return;
        
        bar.style.width = `${Math.max(0, Math.min(100, value))}%`;
        bar.textContent = text || `${value.toFixed(1)}% - ${grade}`;
        
        // 颜色
        bar.className = 'progress-bar ';
        if (value > 95) {
            bar.className += 'bg-success';
        } else if (value > 80) {
            bar.className += 'bg-info';
        } else if (value > 60) {
            bar.className += 'bg-warning';
        } else {
            bar.className += 'bg-danger';
        }
    }
    
    /**
     * 设置导出功能
     */
    setupExport() {
        document.getElementById('download-json')?.addEventListener('click', () => {
            this.downloadFile('results.json', JSON.stringify(this.data, null, 2), 'application/json');
        });
        
        document.getElementById('download-csv')?.addEventListener('click', () => {
            this.exportCSV();
        });
        
        document.getElementById('download-plots')?.addEventListener('click', () => {
            this.downloadAllPlots();
        });
    }
    
    /**
     * 导出CSV
     */
    exportCSV() {
        const x = this.data.geometry.dimensions.spatial.values;
        const variables = this.data.variables;
        
        // 取最后时刻
        let csv = 'Distance_m';
        for (const [key, varData] of Object.entries(variables)) {
            csv += `,${varData.name}_${varData.unit}`;
        }
        csv += '\n';
        
        x.forEach((xi, i) => {
            csv += xi.toFixed(4);
            for (const [key, varData] of Object.entries(variables)) {
                const data = varData.data;
                const timeIdx = data.length - 1;
                csv += `,${data[timeIdx][i].toFixed(6)}`;
            }
            csv += '\n';
        });
        
        this.downloadFile('spatial_profile.csv', csv, 'text/csv');
    }
    
    /**
     * 下载所有图表
     */
    downloadAllPlots() {
        const plotIds = ['plot-longitudinal', 'plot-spatial-distribution', 'plot-time-series', 'plot-contour'];
        
        plotIds.forEach(id => {
            const plot = document.getElementById(id);
            if (plot && plot.data) {
                Plotly.downloadImage(plot, {
                    format: 'png',
                    width: 1200,
                    height: 800,
                    filename: id
                });
            }
        });
        
        alert('图表下载已开始，请检查浏览器下载文件夹');
    }
    
    /**
     * 下载文件
     */
    downloadFile(filename, content, mimeType) {
        const blob = new Blob([content], {type: mimeType});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }
    
    /**
     * 获取变量颜色
     */
    getVariableColor(variable) {
        const colors = {
            'depth': 'rgb(31, 119, 180)',
            'flow': 'rgb(44, 160, 44)',
            'velocity': 'rgb(255, 127, 14)',
            'froude': 'rgb(214, 39, 40)',
            'elevation': 'rgb(148, 103, 189)'
        };
        return colors[variable] || 'rgb(100, 100, 100)';
    }
    
    /**
     * 显示错误
     */
    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show';
        errorDiv.innerHTML = `
            <strong>错误!</strong> ${message}
            <button type="button" class="close" data-dismiss="alert">&times;</button>
        `;
        document.body.insertBefore(errorDiv, document.body.firstChild);
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing viewer...');
    
    // 加载结果数据
    fetch('results.json')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Results data loaded', data);
            const viewer = new HydroViewer(data);
            viewer.init();
        })
        .catch(error => {
            console.error('Failed to load results:', error);
            document.body.innerHTML = `
                <div class="container mt-5">
                    <div class="alert alert-danger">
                        <h4>加载失败</h4>
                        <p>无法加载results.json文件: ${error.message}</p>
                        <p>请确保results.json文件存在且格式正确。</p>
                    </div>
                </div>
            `;
        });
});
