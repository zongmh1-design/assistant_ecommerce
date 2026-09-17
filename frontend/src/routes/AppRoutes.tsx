import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '../auth/ProtectedRoute'
import { WriteRoute } from '../auth/WriteRoute'
import { AppLayout } from '../layouts/AppLayout'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { ProductCreatePage } from '../pages/ProductCreatePage'
import { ProductEditPage } from '../pages/ProductEditPage'
import { ProductListPage } from '../pages/ProductListPage'
import { ProductWorkbenchPage } from '../pages/ProductWorkbenchPage'
import { StoreListPage } from '../pages/StoreListPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/products" replace />} />
          <Route path="/stores" element={<StoreListPage />} />
          <Route path="/products" element={<ProductListPage />} />
          <Route path="/products/:productId" element={<ProductWorkbenchPage />} />
          <Route path="/products/:productId/:moduleKey" element={<ProductWorkbenchPage />} />
          <Route element={<WriteRoute />}>
            <Route path="/products/new" element={<ProductCreatePage />} />
            <Route path="/products/:productId/edit" element={<ProductEditPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  )
}
