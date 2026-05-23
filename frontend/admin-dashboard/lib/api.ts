// ============================================================================
// API CLIENT - Cliente para comunicarse con el backend
// ============================================================================

import axios, { AxiosInstance, AxiosError } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Interceptor para agregar token automáticamente
    this.client.interceptors.request.use((config) => {
      const token = this.getToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Interceptor para manejar errores
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          this.clearToken();
          window.location.href = '/';
        }
        return Promise.reject(error);
      }
    );
  }

  // ============================================================================
  // TOKEN MANAGEMENT
  // ============================================================================

  getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('token');
  }

  setToken(token: string): void {
    if (typeof window === 'undefined') return;
    localStorage.setItem('token', token);
  }

  clearToken(): void {
    if (typeof window === 'undefined') return;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }

  // ============================================================================
  // AUTH
  // ============================================================================

  async login(email: string, password: string) {
    const { data } = await this.client.post('/api/v1/auth/login', {
      email,
      password,
    });
    this.setToken(data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    return data;
  }

  async getMe() {
    const { data } = await this.client.get('/api/v1/auth/me');
    return data;
  }

  async changePassword(currentPassword: string, newPassword: string) {
    const { data } = await this.client.post('/api/v1/auth/password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return data;
  }

  logout() {
    this.clearToken();
    window.location.href = '/';
  }

  // ============================================================================
  // RESTAURANTS
  // ============================================================================

  async getRestaurant(restaurantId: string) {
    const { data } = await this.client.get(`/api/v1/restaurants/${restaurantId}`);
    return data;
  }

  async getRestaurantStats(restaurantId: string) {
    const { data } = await this.client.get(`/api/v1/restaurants/${restaurantId}/stats`);
    return data;
  }

  async updateRestaurant(restaurantId: string, updates: any) {
    const { data } = await this.client.patch(`/api/v1/restaurants/${restaurantId}`, updates);
    return data;
  }

  // ============================================================================
  // PRODUCTS
  // ============================================================================

  async getProducts(restaurantId: string, params?: any) {
    const { data } = await this.client.get(
      `/api/v1/restaurants/${restaurantId}/products`,
      { params }
    );
    return data;
  }

  async getProduct(restaurantId: string, productId: string) {
    const { data } = await this.client.get(
      `/api/v1/restaurants/${restaurantId}/products/${productId}`
    );
    return data;
  }

  async createProduct(restaurantId: string, product: any) {
    const { data } = await this.client.post(
      `/api/v1/restaurants/${restaurantId}/products`,
      product
    );
    return data;
  }

  async updateProduct(restaurantId: string, productId: string, updates: any) {
    const { data } = await this.client.patch(
      `/api/v1/restaurants/${restaurantId}/products/${productId}`,
      updates
    );
    return data;
  }

  async deleteProduct(restaurantId: string, productId: string) {
    const { data } = await this.client.delete(
      `/api/v1/restaurants/${restaurantId}/products/${productId}`
    );
    return data;
  }

  async updateStock(
    restaurantId: string,
    productId: string,
    quantity: number,
    operation: 'set' | 'add' | 'subtract'
  ) {
    const { data } = await this.client.patch(
      `/api/v1/restaurants/${restaurantId}/products/${productId}/stock?operation=${operation}`,
      { quantity }
    );
    return data;
  }

  // ============================================================================
  // CATEGORIES
  // ============================================================================

  async getCategories(restaurantId: string) {
    const { data } = await this.client.get(
      `/api/v1/restaurants/${restaurantId}/categories`
    );
    return data;
  }

  async createCategory(restaurantId: string, category: any) {
    const { data } = await this.client.post(
      `/api/v1/restaurants/${restaurantId}/categories`,
      category
    );
    return data;
  }

  async updateCategory(restaurantId: string, categoryId: string, updates: any) {
    const { data } = await this.client.patch(
      `/api/v1/restaurants/${restaurantId}/categories/${categoryId}`,
      updates
    );
    return data;
  }

  async deleteCategory(restaurantId: string, categoryId: string) {
    const { data } = await this.client.delete(
      `/api/v1/restaurants/${restaurantId}/categories/${categoryId}`
    );
    return data;
  }

  // ============================================================================
  // ORDERS
  // ============================================================================

  async getOrders(restaurantId: string, params?: any) {
    const { data } = await this.client.get(
      `/api/v1/restaurants/${restaurantId}/orders`,
      { params }
    );
    return data;
  }

  async getOrder(restaurantId: string, orderId: string) {
    const { data } = await this.client.get(
      `/api/v1/restaurants/${restaurantId}/orders/${orderId}`
    );
    return data;
  }

  async updateOrderStatus(restaurantId: string, orderId: string, status: string) {
    const { data } = await this.client.patch(
      `/api/v1/restaurants/${restaurantId}/orders/${orderId}`,
      { status }
    );
    return data;
  }

  async getOrdersStats(restaurantId: string, period: string = 'today') {
    const { data } = await this.client.get(
      `/api/v1/restaurants/${restaurantId}/orders/-/stats?period=${period}`
    );
    return data;
  }

  async cancelOrder(restaurantId: string, orderId: string, reason?: string) {
    const { data } = await this.client.post(
      `/api/v1/restaurants/${restaurantId}/orders/${orderId}/cancel`,
      { reason }
    );
    return data;
  }

  // ============================================================================
  // CUSTOMERS
  // ============================================================================

  async getCustomers(restaurantId: string, params?: any) {
    const { data } = await this.client.get(
      `/api/v1/restaurants/${restaurantId}/customers`,
      { params }
    );
    return data;
  }

  async getCustomer(restaurantId: string, phone: string) {
    const { data } = await this.client.get(
      `/api/v1/restaurants/${restaurantId}/customers/${phone}`
    );
    return data;
  }

  async getCustomerOrders(restaurantId: string, phone: string) {
    const { data } = await this.client.get(
      `/api/v1/restaurants/${restaurantId}/customers/${phone}/orders`
    );
    return data;
  }

  async getCustomerLoyalty(restaurantId: string, phone: string) {
    const { data } = await this.client.get(
      `/api/v1/restaurants/${restaurantId}/customers/${phone}/loyalty`
    );
    return data;
  }

  async getCustomersStats(restaurantId: string) {
    const { data } = await this.client.get(
      `/api/v1/restaurants/${restaurantId}/customers/-/stats`
    );
    return data;
  }
}

export const api = new ApiClient();
