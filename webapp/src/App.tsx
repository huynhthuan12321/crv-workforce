import { FC } from "react";

import { ProfilePage } from "./pages/ProfilePage";
import { useTelegram } from "./hooks/useTelegram";
import "./styles/globals.css";
import "./styles/telegram-theme.css";

const App: FC = () => {
  const { colorScheme } = useTelegram();

  return (
    <div className={`app app--${colorScheme}`}>
      <ProfilePage />
    </div>
  );
};

export default App;
