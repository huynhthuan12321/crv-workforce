import { useCallback } from "react";

import { usersApi } from "../api";
import { useUserStore } from "../store/useUserStore";

export const useProfile = () => {
  const { updateBio, setError, setLoading } = useUserStore();

  const saveBio = useCallback(
    async (bio: string) => {
      setLoading(true);
      try {
        await usersApi.updateMe({ bio });
        updateBio(bio);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка сохранения");
      }
    },
    [setLoading, setError, updateBio]
  );

  return { saveBio };
};
