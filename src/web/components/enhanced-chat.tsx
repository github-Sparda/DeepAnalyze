"use client";

import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  Send, 
  Paperclip, 
  Mic, 
  Square,
  Sparkles,
  User,
  Bot,
  FileText,
  Image,
  Trash2,
  Download,
  Copy,
  ThumbsUp,
  ThumbsDown
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  attachments?: Attachment[];
  status?: 'sending' | 'sent' | 'error';
}

interface Attachment {
  id: string;
  name: string;
  type: 'file' | 'image' | 'data';
  size?: string;
  preview?: string;
}

export function EnhancedChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: '您好！我是您的数据分析AI助手。我可以帮您分析数据、生成报告、解答问题。请上传您的数据文件或告诉我您想分析什么？',
      timestamp: new Date(Date.now() - 300000),
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 发送消息
  const sendMessage = async () => {
    if ((!inputValue.trim() && attachments.length === 0) || isSending) return;

    const newMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
      attachments: [...attachments],
      status: 'sending'
    };

    setMessages(prev => [...prev, newMessage]);
    setInputValue('');
    setAttachments([]);
    setIsSending(true);

    // 模拟AI回复
    setTimeout(() => {
      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `我收到了您的消息${attachments.length > 0 ? `和${attachments.length}个附件` : ''}。让我来帮您分析这些数据...`,
        timestamp: new Date(),
        status: 'sent'
      };
      
      setMessages(prev => {
        const updated = [...prev];
        const userMsgIndex = updated.findIndex(msg => msg.id === newMessage.id);
        if (userMsgIndex !== -1) {
          updated[userMsgIndex] = { ...updated[userMsgIndex], status: 'sent' };
        }
        return [...updated, aiResponse];
      });
      setIsSending(false);
    }, 1500);
  };

  // 处理文件上传
  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) return;

    Array.from(files).forEach(file => {
      const attachment: Attachment = {
        id: Date.now().toString() + Math.random(),
        name: file.name,
        type: file.type.startsWith('image/') ? 'image' : 'file',
        size: formatFileSize(file.size),
        preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined
      };
      setAttachments(prev => [...prev, attachment]);
    });
  };

  // 移除附件
  const removeAttachment = (id: string) => {
    setAttachments(prev => prev.filter(att => att.id !== id));
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 处理键盘事件
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full max-w-6xl mx-auto">
      {/* 聊天头部 */}
      <div className="border-b p-4 bg-muted/30">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" />
              AI数据分析助手
            </h2>
            <p className="text-sm text-muted-foreground">
              随时为您提供建议和帮助
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              在线
            </Badge>
            <Button variant="outline" size="sm">
              清空对话
            </Button>
          </div>
        </div>
      </div>

      {/* 消息区域 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.map((message) => (
          <MessageBubble 
            key={message.id} 
            message={message} 
            onRetry={() => console.log('Retry message')}
          />
        ))}
        {isSending && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-2xl rounded-bl-none px-4 py-3 max-w-xs">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
                <span className="text-sm text-muted-foreground">AI正在思考...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 附件预览区域 */}
      {attachments.length > 0 && (
        <div className="border-y bg-muted/30 p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">已添加 {attachments.length} 个附件</span>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => setAttachments([])}
            >
              <Trash2 className="w-4 h-4 mr-1" />
              清除
            </Button>
          </div>
          <div className="flex gap-2 flex-wrap">
            {attachments.map((attachment) => (
              <AttachmentPreview 
                key={attachment.id}
                attachment={attachment}
                onRemove={() => removeAttachment(attachment.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* 输入区域 */}
      <div className="border-t p-4 bg-background">
        <div className="flex gap-3">
          {/* 左侧工具按钮 */}
          <div className="flex flex-col gap-2">
            <Button
              variant="outline"
              size="icon"
              className="rounded-full"
              onClick={() => document.getElementById('file-upload')?.click()}
            >
              <Paperclip className="w-4 h-4" />
            </Button>
            <input
              id="file-upload"
              type="file"
              multiple
              className="hidden"
              onChange={handleFileUpload}
              accept=".csv,.xlsx,.xls,.json,.txt,.png,.jpg,.jpeg"
            />
            
            <Button
              variant={isRecording ? "destructive" : "outline"}
              size="icon"
              className="rounded-full"
              onClick={() => setIsRecording(!isRecording)}
            >
              {isRecording ? <Square className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </Button>
          </div>

          {/* 输入框 */}
          <div className="flex-1">
            <Textarea
              placeholder="输入您的问题或指令... (Shift+Enter换行)"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyPress}
              className="min-h-[60px] resize-none"
              disabled={isSending}
            />
            <div className="flex items-center justify-between mt-2">
              <div className="text-xs text-muted-foreground">
                支持 Markdown 格式 • 可上传文件
              </div>
              <Button 
                onClick={sendMessage}
                disabled={(!inputValue.trim() && attachments.length === 0) || isSending}
                className="gap-2"
              >
                {isSending ? (
                  <>
                    <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                    发送中...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    发送
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ 
  message, 
  onRetry 
}: { 
  message: Message; 
  onRetry: () => void; 
}) {
  const isUser = message.role === 'user';
  
  return (
    <div className={cn(
      "flex gap-3",
      isUser ? "justify-end" : "justify-start"
    )}>
      {!isUser && (
        <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-primary-foreground flex-shrink-0">
          <Bot className="w-4 h-4" />
        </div>
      )}
      
      <div className={cn(
        "max-w-3xl",
        isUser ? "order-first" : ""
      )}>
        <div className={cn(
          "rounded-2xl px-4 py-3",
          isUser 
            ? "bg-primary text-primary-foreground rounded-br-none" 
            : "bg-muted rounded-bl-none"
        )}>
          {/* 附件显示 */}
          {message.attachments && message.attachments.length > 0 && (
            <div className="mb-3 space-y-2">
              {message.attachments.map((attachment) => (
                <div key={attachment.id} className="flex items-center gap-2 text-sm opacity-90">
                  {attachment.type === 'image' ? (
                    <Image className="w-4 h-4" />
                  ) : (
                    <FileText className="w-4 h-4" />
                  )}
                  <span>{attachment.name}</span>
                  {attachment.size && (
                    <span className="text-xs">({attachment.size})</span>
                  )}
                </div>
              ))}
            </div>
          )}
          
          {/* 消息内容 */}
          <div className="whitespace-pre-wrap break-words">
            {message.content}
          </div>
        </div>
        
        {/* 消息底部信息 */}
        <div className={cn(
          "flex items-center gap-2 mt-1 text-xs text-muted-foreground",
          isUser ? "justify-end" : "justify-start"
        )}>
          <span>
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
          
          {message.status === 'error' && (
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-5 px-2 text-xs"
              onClick={onRetry}
            >
              重试
            </Button>
          )}
          
          {!isUser && message.status === 'sent' && (
            <div className="flex gap-1">
              <Button variant="ghost" size="icon" className="h-6 w-6">
                <Copy className="w-3 h-3" />
              </Button>
              <Button variant="ghost" size="icon" className="h-6 w-6">
                <ThumbsUp className="w-3 h-3" />
              </Button>
              <Button variant="ghost" size="icon" className="h-6 w-6">
                <ThumbsDown className="w-3 h-3" />
              </Button>
            </div>
          )}
        </div>
      </div>
      
      {isUser && (
        <div className="w-8 h-8 bg-secondary rounded-full flex items-center justify-center text-secondary-foreground flex-shrink-0">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  );
}

function AttachmentPreview({ 
  attachment, 
  onRemove 
}: { 
  attachment: Attachment; 
  onRemove: () => void; 
}) {
  return (
    <div className="relative group">
      <Card className="w-24 h-24 flex flex-col items-center justify-center p-2 cursor-pointer hover:shadow-md transition-shadow">
        {attachment.preview ? (
          <img 
            src={attachment.preview} 
            alt={attachment.name}
            className="w-full h-full object-cover rounded"
          />
        ) : (
          <div className="flex flex-col items-center">
            <FileText className="w-8 h-8 text-muted-foreground mb-1" />
            <span className="text-xs text-center truncate w-full">
              {attachment.name}
            </span>
            {attachment.size && (
              <span className="text-xs text-muted-foreground">
                {attachment.size}
              </span>
            )}
          </div>
        )}
      </Card>
      <Button
        variant="destructive"
        size="icon"
        className="absolute -top-2 -right-2 w-6 h-6 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={onRemove}
      >
        <Trash2 className="w-3 h-3" />
      </Button>
    </div>
  );
}