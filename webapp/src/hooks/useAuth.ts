import { useCallback } from "react";

import { authApi } from "../api";
import { useUserStore } from "../store/useUserStore";

export const useAuth = () => {
  const { setUser, setError, setLoading } = useUserStore();

  const validate = useCallback(async () => {
    setLoading(true);
    try {
      const response = await authApi.validate();
      if (response.data) {
        setUser(response.data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка загрузки");
    }
  }, [setUser, setError, setLoading]);

  return { validate };
};
