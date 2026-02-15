declare module '@tanstack/react-query' {
  import * as React from 'react';

  export interface QueryClientConfig {
    defaultOptions?: {
      queries?: {
        refetchOnWindowFocus?: boolean;
        retry?: number | boolean;
        staleTime?: number;
        [key: string]: any;
      };
      mutations?: Record<string, any>;
    };
  }

  export class QueryClient {
    constructor(config?: QueryClientConfig);
  }

  export interface QueryClientProviderProps {
    client: QueryClient;
    children?: React.ReactNode;
  }

  export const QueryClientProvider: React.FC<QueryClientProviderProps>;

  export function useQuery(options: any): any;
  export function useMutation(options: any): any;
  export function useQueryClient(): QueryClient;
}
