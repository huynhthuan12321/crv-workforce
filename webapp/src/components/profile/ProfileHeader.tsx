import { FC } from "react";

import { Avatar } from "../common/Avatar";
import { useTelegram } from "../../hooks/useTelegram";
import "./ProfileHeader.css";

interface ProfileHeaderProps {
  firstName?: string | null;
  lastName?: string | null;
  username?: string | null;
  photoUrl?: string | null;
}

export const ProfileHeader: FC<ProfileHeaderProps> = ({
  firstName,
  lastName,
  username,
  photoUrl
}) => {
  const { user: tgUser } = useTelegram();
  const displayName = [firstName, lastName].filter(Boolean).join(" ") || "User";
  const photo = photoUrl || tgUser?.photo_url;

  return (
    <div className="profile-header">
      <Avatar src={photo} name={displayName} size="xl" />
      <h1 className="profile-header__name">{displayName}</h1>
      {username && (
        <span className="profile-header__username">@{username}</span>
      )}
    </div>
  );
};
