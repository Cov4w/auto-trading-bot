/**
 * Main Dashboard Page
 * 트레이딩 봇 대시보드 메인 페이지
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import api from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import StatusCard from '../components/StatusCard';
import ControlPanel from '../components/ControlPanel';
import TradeHistory from '../components/TradeHistory';
import RecommendationsList from '../components/RecommendationsList';
import ModelPerformance from '../components/ModelPerformance';
import CurrentPositions from '../components/CurrentPositions';
import TradingSettings from '../components/TradingSettings';
import '../styles/dashboard.css';

export default function Dashboard() {
  const queryClient = useQueryClient();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [wsConnected, setWsConnected] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());

  // Queries with optimized settings
  const { data: statusData } = useQuery({
    queryKey: ['botStatus'],
    queryFn: async () => {
      const res = await api.bot.getStatus();
      return res.data;
    },
    refetchInterval: 10000, // 10초마다 자동 갱신
    refetchOnWindowFocus: false, // 창 포커스 시 자동 refetch 비활성화
    staleTime: 5000, // 5초간 fresh 상태 유지
  });

  const { data: balanceData } = useQuery({
    queryKey: ['balance'],
    queryFn: async () => {
      const res = await api.data.getBalance();
      return res.data;
    },
    refetchInterval: 15000, // 15초마다 자동 갱신
    refetchOnWindowFocus: false,
    staleTime: 10000,
  });

  const { data: positionsData } = useQuery({
    queryKey: ['positions'],
    queryFn: async () => {
      const res = await api.data.getPositions();
      return res.data.data;
    },
    refetchInterval: 10000,
    refetchOnWindowFocus: false,
    staleTime: 5000,
  });

  const { data: recommendationsData } = useQuery({
    queryKey: ['recommendations'],
    queryFn: async () => {
      const res = await api.data.getRecommendations();
      return res.data;
    },
    refetchInterval: 30000, // 30초마다 (추천은 덜 빈번하게)
    refetchOnWindowFocus: false,
    staleTime: 20000,
  });

  // Mutations
  const startBotMutation = useMutation({
    mutationFn: () => api.bot.start(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['botStatus'] });
    },
  });

  const stopBotMutation = useMutation({
    mutationFn: () => api.bot.stop(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['botStatus'] });
    },
  });

  const updateRecommendationsMutation = useMutation({
    mutationFn: () => api.bot.updateRecommendations(),
    onSuccess: () => {
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      }, 3000);
    },
  });

  const retrainMutation = useMutation({
    mutationFn: () => api.bot.retrain(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['botStatus'] });
    },
  });

  // 실시간 시계 업데이트
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // WebSocket 연결 (탭 전환 시에도 안정적 유지)
  useEffect(() => {
    let ws: WebSocket | null = null;
    let pingInterval: ReturnType<typeof setInterval> | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
    let isUnmounting = false;
    let isTabHidden = false;
    let reconnectAttempts = 0;
    const maxReconnectDelay = 30000; // 최대 30초

    const cleanup = () => {
      if (pingInterval) {
        clearInterval(pingInterval);
        pingInterval = null;
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
      }
    };

    const getReconnectDelay = () => {
      // 지수 백오프: 1초, 2초, 4초, 8초... 최대 30초
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), maxReconnectDelay);
      return delay;
    };

    const connect = () => {
      if (isUnmounting) return;

      // 기존 연결이 있으면 정리
      if (ws && ws.readyState !== WebSocket.CLOSED) {
        ws.close();
      }
      cleanup();

      try {
        ws = api.ws.connectLive();

        ws.onopen = () => {
          console.log('WebSocket connected');
          setWsConnected(true);
          reconnectAttempts = 0; // 연결 성공 시 재시도 횟수 리셋

          // Ping 전송 (keep-alive) - 30초마다 (백그라운드 탭에서도 동작하도록)
          pingInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
              ws.send('ping');
            }
          }, 30000);
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);

            // heartbeat, pong은 무시 (로깅도 하지 않음)
            if (message.type === 'heartbeat' || message.type === 'pong') {
              return;
            }

            if (message.type === 'update' || message.type === 'status') {
              queryClient.invalidateQueries({
                queryKey: ['botStatus'],
                refetchType: 'none'
              });
              queryClient.invalidateQueries({
                queryKey: ['positions'],
                refetchType: 'none'
              });
            }
          } catch (e) {
            // JSON 파싱 에러는 무시 (ping 텍스트 등)
          }
        };

        ws.onclose = (event) => {
          // 정상 종료(1000)나 탭 숨김 상태에서는 로깅 최소화
          if (event.code !== 1000 && !isTabHidden) {
            console.log(`WebSocket disconnected (code: ${event.code})`);
          }
          setWsConnected(false);
          cleanup();

          // 탭이 보이는 상태에서만 자동 재연결
          if (!isUnmounting && !isTabHidden) {
            reconnectAttempts++;
            const delay = getReconnectDelay();
            reconnectTimeout = setTimeout(connect, delay);
          }
        };

        ws.onerror = () => {
          // 에러 로깅 최소화 (onclose에서 처리됨)
        };
      } catch (error) {
        setWsConnected(false);
        // 연결 실패 시 재시도
        if (!isUnmounting && !isTabHidden) {
          reconnectAttempts++;
          const delay = getReconnectDelay();
          reconnectTimeout = setTimeout(connect, delay);
        }
      }
    };

    // 탭 가시성 변경 핸들러
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // 탭이 숨겨짐 - ping은 계속 유지 (브라우저가 알아서 throttle)
        isTabHidden = true;
        // 재연결 타이머만 정리 (ping은 유지)
        if (reconnectTimeout) {
          clearTimeout(reconnectTimeout);
          reconnectTimeout = null;
        }
      } else {
        // 탭이 다시 보임 - 즉시 연결 상태 확인
        isTabHidden = false;
        reconnectAttempts = 0; // 탭 복귀 시 재시도 횟수 리셋
        if (!ws || ws.readyState !== WebSocket.OPEN) {
          // 탭 복귀 시 즉시 재연결 시도
          connect();
        }
      }
    };

    // 이벤트 리스너 등록
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // 초기 연결
    connect();

    return () => {
      isUnmounting = true;
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      cleanup();
      if (ws) {
        ws.close(1000, 'Component unmounting');
        ws = null;
      }
    };
  }, [queryClient]);

  const handleStartBot = () => startBotMutation.mutate();
  const handleStopBot = () => stopBotMutation.mutate();
  const handleUpdateRecommendations = () => updateRecommendationsMutation.mutate();
  const handleRetrain = () => retrainMutation.mutate();

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="dashboard-header">
        <h1>🤖 Self-Evolving Trading System</h1>
        <div className="header-status">
          <span className="user-info">
            👤 {user?.username || user?.email}
          </span>
          <button onClick={toggleTheme} className="theme-toggle" title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}>
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
          <button onClick={logout} className="logout-button">
            Logout
          </button>
          <span className={wsConnected ? 'status-dot connected' : 'status-dot'}>
            {wsConnected ? '🟢 Connected' : '🔴 Disconnected'}
          </span>
          <span className="timestamp">{currentTime.toLocaleTimeString('ko-KR')}</span>
        </div>
      </header>

      {/* Main Content */}
      <div className="dashboard-content">
        {/* Left Column - Controls & Status */}
        <div className="column left-column">
          <ControlPanel
            isRunning={statusData?.is_running || false}
            onStart={handleStartBot}
            onStop={handleStopBot}
            onUpdateRecommendations={handleUpdateRecommendations}
            onRetrain={handleRetrain}
            balance={balanceData}
          />

          <TradingSettings />

          <StatusCard
            status={statusData}
            positions={positionsData?.positions || []}
          />
        </div>

        {/* Center Column - Performance & Positions */}
        <div className="column center-column">
          <ModelPerformance />

          <CurrentPositions />
        </div>

        {/* Right Column - Recommendations & History */}
        <div className="column right-column">
          <RecommendationsList
            recommendations={recommendationsData?.recommendations || []}
            activeTickers={statusData?.tickers || []}
            isUpdating={statusData?.is_updating_recommendations || false}
          />

          <TradeHistory />
        </div>
      </div>
    </div>
  );
}
