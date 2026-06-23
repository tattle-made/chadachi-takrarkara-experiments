import { createFileRoute } from "@tanstack/react-router"
import { CurrentUserPoc } from "@/components/CurrentUserPoc"

export const Route = createFileRoute("/_userLayout/")({
  component: Index,
})

function Index() {
  return <CurrentUserPoc />
}
