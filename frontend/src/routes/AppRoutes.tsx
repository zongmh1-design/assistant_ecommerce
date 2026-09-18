import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '../auth/ProtectedRoute'
import { WriteRoute } from '../auth/WriteRoute'
import { AppLayout } from '../layouts/AppLayout'
import { PageLoading } from '../components/PageState'
import { LoginPage } from '../pages/LoginPage'

const NotFoundPage = lazy(() => import('../pages/NotFoundPage').then(({ NotFoundPage }) => ({ default: NotFoundPage })))
const ProductCreatePage = lazy(() => import('../pages/ProductCreatePage').then(({ ProductCreatePage }) => ({ default: ProductCreatePage })))
const ProductEditPage = lazy(() => import('../pages/ProductEditPage').then(({ ProductEditPage }) => ({ default: ProductEditPage })))
const ProductListPage = lazy(() => import('../pages/ProductListPage').then(({ ProductListPage }) => ({ default: ProductListPage })))
const ProductWorkbenchPage = lazy(() => import('../pages/ProductWorkbenchPage').then(({ ProductWorkbenchPage }) => ({ default: ProductWorkbenchPage })))
const StoreListPage = lazy(() => import('../pages/StoreListPage').then(({ StoreListPage }) => ({ default: StoreListPage })))

export function AppRoutes() {
  return (
    <Suspense fallback={<PageLoading />}>
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
    </Suspense>
  )
}
