import { Component, type ErrorInfo, type ReactNode } from "react";
import { ErrorState } from "./states";

interface Props {
  message: string;
  children: ReactNode;
}

/** Catches render errors so one broken screen does not blank the whole app. */
export class ErrorBoundary extends Component<Props, { error: Error | null }> {
  override state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(error, info.componentStack);
  }

  override render() {
    if (this.state.error) {
      return (
        <div className="page">
          <ErrorState
            message={this.props.message}
            detail={this.state.error.message}
            onRetry={() => window.location.reload()}
          />
        </div>
      );
    }
    return this.props.children;
  }
}
