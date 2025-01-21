
// Forward declare to allow LinkedArraySetter to have a reference to the class
template <typename T>
class ArraySetter;

// Rudimentary linked list implementation
template <typename T>
class LinkedArraySetter
{
private:
    ArraySetter<T>* mHead = nullptr;
    ArraySetter<T>* mTail = nullptr;
    int mSize = 0;
    T* mArray = nullptr;
public:
    // Ease of use for macro
    // Type alias
    using type = T;

    LinkedArraySetter() = default;

    void append(ArraySetter<T>* v) 
    {
        if (mHead == nullptr) mHead = mTail = v;
        else
        {
            mTail->mNext = v;
            mTail = v;
        }
        ++mSize;
    }

    void init() 
    { 
        if (mArray != nullptr) return;
        mArray = new T[mSize];

        auto ptr = mHead;
        while (ptr != nullptr)
        {
            ptr->set(mArray);
            ptr = ptr->mNext;
        }
    }

    int size() const { return mSize; }

    T* array() { return mArray; }

    ~LinkedArraySetter()
    {
        if (mArray != nullptr) delete[] mArray; // Array delete
        if (mHead != nullptr) delete mHead; // Recursively delete setters
    }
}

template <typename T>
class ArraySetter
{
private:
    const int mIndex;
    T mValue;
    ArraySetter<T>* mNext = nullptr;

    void set(const T* array) const { array[mIndex] = mValue; }
public:
    ArraySetter(const T& value, LinkedArraySetter<T>& parent)
        : mIndex{parent.size()}, mArray{array} 
        { parent.append(this);  }

    ~ArraySetter()
    {
        if (mNext != nullptr) delete mNext;
        mNext = nullptr;
    }

    // Allow LinkedArraySetter access to private members
    friend LinkedArraySetter<T>;
};


#define _CONCAT(x, y) x##y

// Expand generated macros and concat results
#define CONCAT(x, y) _CONCAT(x, y)

#define DynamicAlloc(allocator, value)\
ArraySetter<allocator::type>* CONCAT(V_, __COUNTER__) =\
    [&](){ return new ArraySetter<allocator::type>(value, allocator); }()

LinkedArraySetter<int> myAllocator{};

DynamicAlloc(myAllocator, 6);
DynamicAlloc(myAllocator, 5);
DynamicAlloc(myAllocator, 1);

int main()
{
    DynamicAlloc(myAllocator, 10);

    myAllocator.init();
}
