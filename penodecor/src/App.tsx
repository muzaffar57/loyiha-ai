import { Navigate, Route, Routes, useParams } from "react-router-dom";
import { RequireAdmin } from "./admin/AdminApp";
import { CategoriesPage } from "./admin/CategoriesPage";
import { DashboardPage } from "./admin/DashboardPage";
import { LoginPage } from "./admin/LoginPage";
import { ProductsPage } from "./admin/ProductsPage";
import { StockPage } from "./admin/StockPage";
import { SyncPage } from "./admin/SyncPage";
import { UnpricedPage } from "./admin/UnpricedPage";
import { AppShell } from "./components/AppShell";
import { CartPage } from "./pages/CartPage";
import { CatalogPage } from "./pages/CatalogPage";
import { CategoryPage } from "./pages/CategoryPage";
import { AboutPage, DeliveryPage, FaqPage, PrivacyPage, TermsPage } from "./pages/contentPages";
import { HomePage } from "./pages/HomePage";
import { OrdersPage } from "./pages/OrdersPage";
import { ProductPage } from "./pages/ProductPage";
import { ProfilePage } from "./pages/ProfilePage";

function CategoryRoute() {
  const { slug } = useParams();
  return <CategoryPage key={slug} />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/admin/login" element={<LoginPage />} />
      <Route path="/admin" element={<RequireAdmin />}>
        <Route index element={<DashboardPage />} />
        <Route path="kategoriyalar" element={<CategoriesPage />} />
        <Route path="mahsulotlar" element={<ProductsPage />} />
        <Route path="ombor" element={<StockPage />} />
        <Route path="narxsiz" element={<UnpricedPage />} />
        <Route path="sinxron" element={<SyncPage />} />
      </Route>
      <Route element={<AppShell />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/katalog" element={<CatalogPage />} />
        <Route path="/katalog/:slug" element={<CategoryRoute />} />
        <Route path="/mahsulot/:slug" element={<ProductPage />} />
        <Route path="/savat" element={<CartPage />} />
        <Route path="/buyurtmalar" element={<OrdersPage />} />
        <Route path="/profil" element={<ProfilePage />} />
        <Route path="/kompaniya" element={<AboutPage />} />
        <Route path="/yetkazish" element={<DeliveryPage />} />
        <Route path="/savol-javob" element={<FaqPage />} />
        <Route path="/maxfiylik" element={<PrivacyPage />} />
        <Route path="/shartlar" element={<TermsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
