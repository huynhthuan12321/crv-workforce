import { FC } from "react";
import { useTranslation } from "react-i18next";

import "./ProfileStats.css";

interface ProfileStatsProps {
  telegramId: number;
  dbId: number;
  language: string;
  createdAt: string;
}

export const ProfileStats: FC<ProfileStatsProps> = ({
  telegramId,
  dbId,
  language,
  createdAt
}) => {
  const { t } = useTranslation();
  const stats = [
    { label: t("profile.stats.telegramId"), value: telegramId.toString() },
    { label: t("profile.stats.userId"), value: dbId.toString() },
    { label: t("profile.stats.language"), value: language.toUpperCase() },
    {
      label: t("profile.stats.registeredAt"),
      value: new Date(createdAt).toLocaleDateString()
    }
  ];

  return (
    <div className="profile-stats">
      {stats.map((stat) => (
        <div key={stat.label} className="profile-stats__item">
          <span className="profile-stats__label">{stat.label}</span>
          <span className="profile-stats__value">{stat.value}</span>
        </div>
      ))}
    </div>
  );
};
