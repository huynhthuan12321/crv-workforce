import {Component, type ErrorInfo, type ReactNode} from "react";
import {reportClientError} from "../api/client";
import {Button, Card} from "./ui";

type Props = {children: ReactNode; title?: string; tab?: string; role?: string};
type State = {error: Error | null};

export class ErrorBoundary extends Component<Props, State> {
  state: State = {error: null};

  static getDerivedStateFromError(error: Error): State {
    return {error};
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("CRV UI error", error, info.componentStack);
    reportClientError({
      message: error.message || "Render error",
      stack: `${error.stack ?? ""}\n${info.componentStack ?? ""}`,
      tab: this.props.tab,
      role: this.props.role,
      app_version: import.meta.env.VITE_APP_VERSION || "dev",
    });
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <Card className="state state--error">
        <div className="state__icon">!</div>
        <h2>{this.props.title ?? "Có lỗi hiển thị"}</h2>
        <p>Vui lòng tải lại màn hình. Nếu lỗi lặp lại, báo quản lý để được hỗ trợ.</p>
        <Button tone="secondary" onClick={() => this.setState({error: null})}>Tải lại</Button>
      </Card>
    );
  }
}
