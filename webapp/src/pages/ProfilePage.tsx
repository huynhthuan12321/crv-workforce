import { FC, useEffect } from "react";
import { useTranslation } from "react-i18next";

import { authApi } from "../api/endpoints";
import { ProfileCard } from "../components/profile";
import { Loader } from "../components/common/Loader";
import { useTelegram } from "../hooks/useTelegram";
import { useUserStore } from "../store/useUserStore";
import "./ProfilePage.css";

export const ProfilePage: FC = () => {
  const { t } = useTranslation();
  const { isReady } = useTelegram();
  const { user, isLoading, error, setUser, setError, setLoading } =
    useUserStore();

  useEffect(() => {
    if (!isReady) return;

    const loadUser = async () => {
      setLoading(true);
      try {
        const response = await authApi.validate();
        if (response.data) {
          setUser(response.data);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки");
      }
    };

    loadUser();
  }, [isReady, setUser, setError, setLoading]);

  if (!isReady || isLoading) {
    return (
      <div className="profile-page profile-page--loading">
        <Loader />
      </div>
    );
  }

  if (error) {
    return (
      <div className="profile-page profile-page--error">
        <p>
          {t("common.error")}: {error}
        </p>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <ProfileCard />
    </div>
  );
};
