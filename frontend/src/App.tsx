import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { ProcessFiles } from './pages/ProcessFiles';
import { Brands } from './pages/Brands';
import { BrandEditor } from './pages/BrandEditor';
import { Settings } from './pages/Settings';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/process" element={<ProcessFiles />} />
          <Route path="/brands" element={<Brands />} />
          <Route path="/brands/:brandName" element={<BrandEditor />} />
          <Route path="/brands/new" element={<BrandEditor />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
