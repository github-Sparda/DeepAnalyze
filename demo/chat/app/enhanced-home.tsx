"use client";

import React, { useState } from "react";
import { EnhancedLayout, DashboardView } from "@/components/enhanced-layout";
import { EnhancedChatInterface } from "@/components/enhanced-chat";
import { EnhancedAnalysisView } from "@/components/enhanced-analysis";
import { EnhancedReportView } from "@/components/enhanced-report";
import { EnhancedWorkspaceView } from "@/components/enhanced-workspace";

type ViewMode = 'dashboard' | 'analyze' | 'chat' | 'reports' | 'workspace';

export default function EnhancedHomePage() {
  const [activeView, setActiveView] = useState<ViewMode>('dashboard');

  const renderActiveView = () => {
    switch (activeView) {
      case 'dashboard':
        return <DashboardView />;
      case 'analyze':
        return <EnhancedAnalysisView />;
      case 'chat':
        return <EnhancedChatInterface />;
      case 'reports':
        return <EnhancedReportView />;
      case 'workspace':
        return <EnhancedWorkspaceView />;
      default:
        return <DashboardView />;
    }
  };

  return (
    <EnhancedLayout 
      activeView={activeView} 
      onViewChange={setActiveView}
    >
      {renderActiveView()}
    </EnhancedLayout>
  );
}

// 增强的布局组件（整合版）
interface EnhancedLayoutProps {
  children: React.ReactNode;
  activeView: ViewMode;
  onViewChange: (view: ViewMode) => void;
}

function EnhancedLayout({ 
  children, 
  activeView, 
  onViewChange 
}: EnhancedLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  // 导航菜单项
  const navigationItems = [
    { id: 'dashboard', label: '仪表板', icon: 'Home', route: '/' },
    { id: 'analyze', label: '数据分析', icon: 'BarChart3', route: '/analyze' },
    { id: 'chat', label: 'AI助手', icon: 'MessageCircle', route: '/chat' },
    { id: 'reports', label: '报告中心', icon: 'FileText', route: '/reports' },
    { id: 'workspace', label: '工作区', icon: 'Folder', route: '/workspace' },
  ];

  // 快捷操作
  const quickActions = [
    { id: 'upload', label: '上传数据', icon: 'Upload', action: () => console.log('Upload clicked') },
    { id: 'newChat', label: '新建对话', icon: 'Plus', action: () => console.log('New chat') },
    { id: 'settings', label: '设置', icon: 'Settings', action: () => console.log('Settings') },
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
      <aside className={`bg-muted border-r transition-all duration-300 flex flex-col ${sidebarOpen ? "w-64" : "w-16"}`}>
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
                <button
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-left transition-colors ${
                    activeView === item.id 
                      ? "bg-secondary text-secondary-foreground" 
                      : "hover:bg-muted"
                  } ${!sidebarOpen && "justify-center px-2"}`}
                  onClick={() => onViewChange(item.id as ViewMode)}
                >
                  <Icon iconName={item.icon} className="w-4 h-4" />
                  {sidebarOpen && <span>{item.label}</span>}
                  {!sidebarOpen && <span className="sr-only">{item.label}</span>}
                </button>
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
                  <button
                    key={action.id}
                    className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-left text-sm hover:bg-muted transition-colors"
                    onClick={action.action}
                  >
                    <Icon iconName={action.icon} className="w-4 h-4" />
                    <span>{action.label}</span>
                  </button>
                ))}
              </div>
            )}

            {/* 主题切换和菜单开关 */}
            <div className="flex gap-1">
              <button
                className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted transition-colors flex-1"
                onClick={toggleTheme}
              >
                {theme === 'light' ? 
                  <Moon className="w-4 h-4" /> : 
                  <Sun className="w-4 h-4" />
                }
                {sidebarOpen && <span>{theme === 'light' ? '深色' : '浅色'}</span>}
              </button>
              
              <button
                className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted transition-colors flex-1"
                onClick={toggleSidebar}
              >
                {sidebarOpen ? 
                  <X className="w-4 h-4" /> : 
                  <Menu className="w-4 h-4" />
                }
                {sidebarOpen && <span>收起</span>}
              </button>
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
                {getViewDescription(activeView)}
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

// 图标组件
function Icon({ iconName, className }: { iconName: string; className?: string }) {
  const icons: Record<string, React.ReactNode> = {
    Home: <Home className={className} />,
    BarChart3: <BarChart3 className={className} />,
    MessageCircle: <MessageCircle className={className} />,
    FileText: <FileText className={className} />,
    Folder: <Folder className={className} />,
    Upload: <Upload className={className} />,
    Plus: <Plus className={className} />,
    Settings: <Settings className={className} />,
    Moon: <Moon className={className} />,
    Sun: <Sun className={className} />,
    Menu: <Menu className={className} />,
    X: <X className={className} />,
  };
  
  return icons[iconName] || <div className={className} />;
}

// 获取视图描述
function getViewDescription(viewId: ViewMode): string {
  const descriptions: Record<ViewMode, string> = {
    dashboard: '概览项目状态和快速访问常用功能',
    analyze: '上传数据文件并进行智能分析',
    chat: '与AI助手对话，获得分析建议和帮助',
    reports: '查看、编辑和导出分析报告',
    workspace: '管理项目文件和工作区资源'
  };
  return descriptions[viewId];
}

// 导入所需的图标组件
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

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

// 占位组件（后续实现具体功能）
function EnhancedAnalysisView() {
  return (
    <div className="flex items-center justify-center h-96">
      <div className="text-center">
        <BarChart3 className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
        <h3 className="text-xl font-semibold mb-2">数据分析视图</h3>
        <p className="text-muted-foreground">此功能正在开发中...</p>
      </div>
    </div>
  );
}

function EnhancedReportView() {
  return (
    <div className="flex items-center justify-center h-96">
      <div className="text-center">
        <FileText className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
        <h3 className="text-xl font-semibold mb-2">报告中心</h3>
        <p className="text-muted-foreground">此功能正在开发中...</p>
      </div>
    </div>
  );
}

function EnhancedWorkspaceView() {
  return (
    <div className="flex items-center justify-center h-96">
      <div className="text-center">
        <Folder className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
        <h3 className="text-xl font-semibold mb-2">工作区管理</h3>
        <p className="text-muted-foreground">此功能正在开发中...</p>
      </div>
    </div>
  );
}