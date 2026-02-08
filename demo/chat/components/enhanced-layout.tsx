"use client";

import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  Home, 
  BarChart3, 
  MessageCircle, 
  FileText, 
  Folder,
  Upload,
  Plus,
  Settings,
  Moon,
  Sun,
  Menu,
  X
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavigationItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  route: string;
}

interface QuickAction {
  id: string;
  label: string;
  icon: React.ReactNode;
  action: () => void;
}

export function EnhancedLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [activeView, setActiveView] = useState('dashboard');

  // 导航菜单项
  const navigationItems: NavigationItem[] = [
    { id: 'dashboard', label: '仪表板', icon: <Home className="w-4 h-4" />, route: '/' },
    { id: 'analyze', label: '数据分析', icon: <BarChart3 className="w-4 h-4" />, route: '/analyze' },
    { id: 'chat', label: 'AI助手', icon: <MessageCircle className="w-4 h-4" />, route: '/chat' },
    { id: 'reports', label: '报告中心', icon: <FileText className="w-4 h-4" />, route: '/reports' },
    { id: 'workspace', label: '工作区', icon: <Folder className="w-4 h-4" />, route: '/workspace' },
  ];

  // 快捷操作
  const quickActions: QuickAction[] = [
    { id: 'upload', label: '上传数据', icon: <Upload className="w-4 h-4" />, action: () => console.log('Upload clicked') },
    { id: 'newChat', label: '新建对话', icon: <Plus className="w-4 h-4" />, action: () => console.log('New chat') },
    { id: 'settings', label: '设置', icon: <Settings className="w-4 h-4" />, action: () => console.log('Settings') },
  ];

  // 切换主题
  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    document.documentElement.classList.toggle('dark', newTheme === 'dark');
  };

  // 切换侧边栏
  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* 侧边栏 */}
      <aside className={cn(
        "bg-muted border-r transition-all duration-300 flex flex-col",
        sidebarOpen ? "w-64" : "w-16"
      )}>
        {/* Logo区域 */}
        <div className="p-4 border-b">
          <div className="flex items-center gap-3">
            <div className="bg-primary text-primary-foreground rounded-lg p-2">
              <BarChart3 className="w-6 h-6" />
            </div>
            {sidebarOpen && (
              <div>
                <h1 className="font-bold text-lg">DeepAnalyze</h1>
                <p className="text-xs text-muted-foreground">智能数据分析</p>
              </div>
            )}
          </div>
        </div>

        {/* 导航菜单 */}
        <nav className="flex-1 p-2">
          <ul className="space-y-1">
            {navigationItems.map((item) => (
              <li key={item.id}>
                <Button
                  variant={activeView === item.id ? "secondary" : "ghost"}
                  className={cn(
                    "w-full justify-start gap-3",
                    !sidebarOpen && "justify-center px-2"
                  )}
                  onClick={() => setActiveView(item.id)}
                >
                  {item.icon}
                  {sidebarOpen && <span>{item.label}</span>}
                  {!sidebarOpen && (
                    <span className="sr-only">{item.label}</span>
                  )}
                </Button>
              </li>
            ))}
          </ul>
        </nav>

        {/* 底部操作 */}
        <div className="p-2 border-t">
          <div className="space-y-2">
            {/* 快捷操作 */}
            {sidebarOpen && (
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground px-2">快捷操作</p>
                {quickActions.map((action) => (
                  <Button
                    key={action.id}
                    variant="ghost"
                    size="sm"
                    className="w-full justify-start gap-3"
                    onClick={action.action}
                  >
                    {action.icon}
                    <span>{action.label}</span>
                  </Button>
                ))}
              </div>
            )}

            {/* 主题切换和菜单开关 */}
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleTheme}
                className={!sidebarOpen ? "flex-1 justify-center" : ""}
              >
                {theme === 'light' ? 
                  <Moon className="w-4 h-4" /> : 
                  <Sun className="w-4 h-4" />
                }
                {sidebarOpen && (
                  <span>{theme === 'light' ? '深色' : '浅色'}</span>
                )}
              </Button>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleSidebar}
                className={!sidebarOpen ? "flex-1 justify-center" : ""}
              >
                {sidebarOpen ? 
                  <X className="w-4 h-4" /> : 
                  <Menu className="w-4 h-4" />
                }
                {sidebarOpen && <span>收起</span>}
              </Button>
            </div>
          </div>
        </div>
      </aside>

      {/* 主内容区域 */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* 顶部状态栏 */}
        <header className="border-b bg-muted/50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold">
                {navigationItems.find(item => item.id === activeView)?.label}
              </h2>
              <p className="text-sm text-muted-foreground">
                {getActiveViewDescription(activeView)}
              </p>
            </div>
            
            <div className="flex items-center gap-2">
              {/* 状态指示器 */}
              <Badge variant="outline" className="gap-1">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                在线
              </Badge>
              
              {/* 用户菜单占位 */}
              <Button variant="ghost" size="sm">
                <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-primary-foreground font-medium">
                  U
                </div>
              </Button>
            </div>
          </div>
        </header>

        {/* 内容区域 */}
        <div className="flex-1 overflow-auto p-6">
          {children}
        </div>

        {/* 底部状态栏 */}
        <footer className="border-t bg-muted/30 p-3">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <div className="flex items-center gap-4">
              <span>DeepAnalyze v1.0</span>
              <span>•</span>
              <span>就绪状态</span>
            </div>
            <div className="flex items-center gap-4">
              <span>帮助文档</span>
              <span>•</span>
              <span>反馈建议</span>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}

function getActiveViewDescription(viewId: string): string {
  const descriptions: Record<string, string> = {
    dashboard: '概览项目状态和快速访问常用功能',
    analyze: '上传数据文件并进行智能分析',
    chat: '与AI助手对话，获得分析建议和帮助',
    reports: '查看、编辑和导出分析报告',
    workspace: '管理项目文件和工作区资源'
  };
  return descriptions[viewId] || '';
}

// 仪表板视图组件
export function DashboardView() {
  const [recentProjects, setRecentProjects] = useState([
    { id: 1, name: '销售数据分析', date: '2024-01-15', status: '已完成' },
    { id: 2, name: '用户行为研究', date: '2024-01-14', status: '进行中' },
    { id: 3, name: '市场趋势预测', date: '2024-01-13', status: '待处理' },
  ]);

  return (
    <div className="space-y-6">
      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="总项目数" value="12" change="+2" />
        <StatCard title="活跃分析" value="3" change="0" />
        <StatCard title="生成报告" value="8" change="+1" />
        <StatCard title="数据集" value="24" change="+5" />
      </div>

      {/* 最近项目 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            最近项目
            <Button variant="outline" size="sm">
              查看全部
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {recentProjects.map((project) => (
              <div key={project.id} className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors">
                <div>
                  <h3 className="font-medium">{project.name}</h3>
                  <p className="text-sm text-muted-foreground">{project.date}</p>
                </div>
                <Badge variant={project.status === '已完成' ? 'default' : project.status === '进行中' ? 'secondary' : 'outline'}>
                  {project.status}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 快速操作 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <QuickActionCard 
          title="开始新分析" 
          description="上传数据文件开始智能分析"
          icon={<BarChart3 className="w-8 h-8" />}
          action={() => console.log('Start analysis')}
        />
        <QuickActionCard 
          title="与AI对话" 
          description="询问数据分析相关问题"
          icon={<MessageCircle className="w-8 h-8" />}
          action={() => console.log('Start chat')}
        />
        <QuickActionCard 
          title="查看报告" 
          description="浏览和导出分析报告"
          icon={<FileText className="w-8 h-8" />}
          action={() => console.log('View reports')}
        />
      </div>
    </div>
  );
}

function StatCard({ title, value, change }: { title: string; value: string; change: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
          </div>
          <Badge variant={change.startsWith('+') ? 'default' : 'secondary'}>
            {change}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}

function QuickActionCard({ 
  title, 
  description, 
  icon, 
  action 
}: { 
  title: string; 
  description: string; 
  icon: React.ReactNode;
  action: () => void;
}) {
  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer" onClick={action}>
      <CardContent className="p-6 text-center">
        <div className="mb-4 text-primary flex justify-center">
          {icon}
        </div>
        <h3 className="font-semibold mb-2">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}