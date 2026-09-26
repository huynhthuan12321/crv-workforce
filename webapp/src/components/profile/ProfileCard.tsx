import { FC, useCallback } from "react";
import { useTranslation } from "react-i18next";

import { useTelegram } from "../../hooks/useTelegram";
import { useUserStore } from "../../store/useUserStore";
import { usersApi } from "../../api/endpoints";
import { BioEditor } from "./BioEditor";
import { ProfileHeader } from "./ProfileHeader";
import { ProfileStats } from "./ProfileStats";
import "./ProfileCard.css";

export const ProfileCard: FC = () => {
  const { t } = useTranslation();
  const { user, updateBio } = useUserStore();
  const { sendData, user: tgUser } = useTelegram();

  const handleSaveBio = useCallback(
    async (bio: string) => {
      await usersApi.updateMe({ bio });
      updateBio(bio);
      sendData({ action: "bio_updated", bio });
    },
    [updateBio, sendData]
  );

  if (!user) {
    return (
      <div className="profile-card profile-card--empty">
        {t("common.loading")}
      </div>
    );
  }

  return (
    <div className="profile-card">
      <ProfileHeader
        firstName={user.first_name}
        lastName={user.last_name}
        username={user.username}
        photoUrl={tgUser?.photo_url}
      />

      <ProfileStats
        telegramId={user.telegram_id}
        dbId={user.id}
        language={user.language_code}
        createdAt={user.created_at}
      />

      <BioEditor bio={user.bio} onSave={handleSaveBio} />
    </div>
  );
};
