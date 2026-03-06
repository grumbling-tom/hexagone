import {
  getGetCurrentUserQueryKey,
  useGetCurrentUser,
} from "@/__generated__/backend-client/users";

export { getGetCurrentUserQueryKey };

export function useAuth() {
  const { data: user, isLoading } = useGetCurrentUser({
    query: { retry: false },
  });

  return {
    user: user ?? null,
    isLoading,
    isAuthenticated: !!user,
  };
}
