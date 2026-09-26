import {ScreenState} from "../../components/ui";

export function PlaceholderScreen({title}: {title: string}) {
  return (
    <ScreenState
      kind="empty"
      title={title}
      message="Màn này không thuộc phạm vi GĐ7b. Component nền đã sẵn sàng để triển khai ở bước tiếp theo."
    />
  );
}
