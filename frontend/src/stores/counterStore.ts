import { create } from "zustand"

/**
 * A POC Zustand state store for counter. 
 * 
 * Usage in a JSX component:
 function Counter() {
  const { count, inc } = useCounterStore()
  return (
    <div>
      <span>{count}</span>
      <button onClick={inc}>one up</button>
    </div>
  )
}
 */

type CounterStore = {
  count: number
  inc: () => void
}

const useCounterStore = create<CounterStore>()((set) => ({
  count: 1,
  inc: () => set((state) => ({ count: state.count + 1 })),
}))

export default useCounterStore
