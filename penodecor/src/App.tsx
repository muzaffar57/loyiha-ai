import { Navigate, Route, Routes, useParams } from "react-router-dom";
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
    <AppShell>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/katalog" element={<CatalogPage />} />
        <Route path="/katalog/:slug" element={<CategoryRoute />} />
        <Route path="/mahsulot/:id" element={<ProductPage />} />
        <Route path="/savat" element={<CartPage />} />
        <Route path="/buyurtmalar" element={<OrdersPage />} />
        <Route path="/profil" element={<ProfilePage />} />
        <Route path="/kompaniya" element={<AboutPage />} />
        <Route path="/yetkazish" element={<DeliveryPage />} />
        <Route path="/savol-javob" element={<FaqPage />} />
        <Route path="/maxfiylik" element={<PrivacyPage />} />
        <Route path="/shartlar" element={<TermsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
