import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export interface TestCase {
  metadata: {
    id: string;
    name: string;
    nameCN: string;
    category: string;
  };
  config: any;
}

export interface TestCaseListResponse {
  total: number;
  cases: TestCase[];
}

export interface TestCaseDetailResponse extends TestCase {}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

export const api = {
  getAllTestCases: async (limit: number = 550, offset: number = 0): Promise<TestCaseListResponse> => {
    const response = await apiClient.get('/test-cases', { params: { limit, offset } });
    return response.data;
  },

  getTestCaseDetail: async (caseId: string): Promise<TestCaseDetailResponse> => {
    const response = await apiClient.get(`/test-cases/detail/${caseId}`);
    return response.data;
  },
};
