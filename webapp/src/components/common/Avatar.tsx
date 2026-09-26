import { FC } from "react";

import "./Avatar.css";

interface AvatarProps {
  src?: string | null;
  name?: string;
  size?: "sm" | "md" | "lg" | "xl";
}

export const Avatar: FC<AvatarProps> = ({ src, name = "?", size = "md" }) => {
  const initials = name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <div className={`avatar avatar--${size}`}>
      {src ? (
        <img src={src} alt={name} className="avatar__image" />
      ) : (
        <span className="avatar__initials">{initials}</span>
      )}
    </div>
  );
};
