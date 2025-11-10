/**
 * Redux Store Configuration
 * Redux Store 配置
 */

import { configureStore } from '@reduxjs/toolkit';
import modelReducer from '@/features/modeling/store/modelSlice';

export const store = configureStore({
  reducer: {
    model: modelReducer
    // 未来可以添加其他reducer:
    // simulation: simulationReducer,
    // user: userReducer,
    // etc.
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // 忽略某些不可序列化的action paths
        ignoredActions: ['model/importModel'],
        ignoredPaths: ['model.currentModel.metadata']
      }
    })
});

// 导出类型
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
