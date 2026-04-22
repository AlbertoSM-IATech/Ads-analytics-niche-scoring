import "./App.css";
import { BrowserRouter } from "react-router-dom";
import { DataProvider } from "./context/DataContext";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import { Toaster } from "sonner";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <DataProvider>
          <div className="flex min-h-screen bg-background text-foreground">
            <Sidebar />
            <Dashboard />
          </div>
          <Toaster
            position="bottom-right"
            toastOptions={{ className: "rounded-sm border border-border" }}
          />
        </DataProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
