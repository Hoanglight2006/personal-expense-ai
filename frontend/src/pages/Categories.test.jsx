import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthContext } from '../context/auth-context';
import CategoryCard from '../components/CategoryCard';
import CategoryFormModal from '../components/CategoryFormModal';
import CategoryIcon from '../components/CategoryIcon';
import Categories from './Categories';
import {
  createCategory,
  createDefaultCategories,
  getCategories,
  hideCategory,
  restoreCategory,
  deleteCategory,
} from '../api/categoryApi';

vi.mock('../api/categoryApi', () => ({
  getCategories: vi.fn(),
  createCategory: vi.fn(),
  createDefaultCategories: vi.fn(),
  updateCategory: vi.fn(),
  hideCategory: vi.fn(),
  restoreCategory: vi.fn(),
  deleteCategory: vi.fn(),
}));

const category = {
  id: 1,
  name: 'Ăn uống',
  type: 'expense',
  icon: 'food',
  color: '#C87941',
  is_active: true,
  is_default: false,
  created_at: '2026-08-01T00:00:00',
  updated_at: '2026-08-01T00:00:00',
  has_transactions: true,
  total_amount: '250000.00',
  income_amount: '0.00',
  expense_amount: '250000.00',
  transaction_count: 3,
  expense_percentage: '25.00',
};

const response = (items = [category]) => ({
  start_date: '2026-08-01',
  end_date: '2026-08-31',
  items,
});

const renderPage = () => render(
  <AuthContext.Provider value={{ user: { username: 'tester' }, logout: vi.fn() }}>
    <MemoryRouter initialEntries={['/categories']}>
      <Categories />
    </MemoryRouter>
  </AuthContext.Provider>,
);

beforeEach(() => {
  vi.clearAllMocks();
  getCategories.mockResolvedValue(response());
  createCategory.mockResolvedValue({ ...category, id: 99, name: 'Đi lại' });
  createDefaultCategories.mockResolvedValue([]);
  hideCategory.mockResolvedValue({ ...category, is_active: false });
  restoreCategory.mockResolvedValue(category);
  deleteCategory.mockResolvedValue({});
});

describe('Categories page', () => {
  it('renders loading then category cards', async () => {
    renderPage();
    expect(screen.getByText('Đang tải danh mục...')).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'Ăn uống' })).toBeInTheDocument();
    expect(screen.getByText(/25.00% tổng chi/)).toBeInTheDocument();
  });

  it('renders API error and empty search state', async () => {
    getCategories.mockRejectedValueOnce({ response: { data: { detail: 'Máy chủ từ chối.' } } });
    const firstRender = renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('Máy chủ từ chối.');
    firstRender.unmount();

    getCategories.mockResolvedValue(response([]));
    renderPage();
    await userEvent.type(screen.getByPlaceholderText('Nhập tên danh mục...'), 'không có');
    expect(await screen.findByText('Không có kết quả phù hợp')).toBeInTheDocument();
  });

  it('distinguishes connection failures from server failures', async () => {
    getCategories.mockRejectedValueOnce({ request: {} });
    const networkRender = renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Không thể kết nối đến máy chủ. Hãy kiểm tra backend hoặc cấu hình mạng.',
    );
    networkRender.unmount();

    getCategories.mockRejectedValueOnce({ response: { status: 500, data: {} } });
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Máy chủ gặp lỗi khi xử lý danh mục.',
    );
  });

  it('creates the suggested category set from the empty state', async () => {
    const user = userEvent.setup();
    getCategories.mockResolvedValue(response([]));
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Dùng bộ danh mục gợi ý' }));
    await waitFor(() => expect(createDefaultCategories).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/Các danh mục gợi ý đã tồn tại/)).toBeInTheDocument();
  });

  it('filters locally without sending another network request', async () => {
    const user = userEvent.setup();
    getCategories.mockResolvedValue(response([
      category,
      { ...category, id: 2, name: 'Lương', icon: 'salary', is_active: false },
    ]));
    renderPage();
    await screen.findByRole('heading', { name: 'Ăn uống' });
    await user.type(screen.getByPlaceholderText('Nhập tên danh mục...'), 'ăn');
    expect(screen.queryByRole('heading', { name: 'Lương' })).not.toBeInTheDocument();
    expect(getCategories).toHaveBeenCalledTimes(1);
  });

  it('opens the add form, prevents repeated submission, and updates locally', async () => {
    const user = userEvent.setup();
    let finishCreate;
    createCategory.mockReturnValue(new Promise((resolve) => { finishCreate = resolve; }));
    renderPage();
    await screen.findByRole('heading', { name: 'Ăn uống' });

    await user.click(screen.getByRole('button', { name: '+ Thêm danh mục' }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    const nameInput = screen.getByLabelText('Tên hiển thị');
    await user.clear(nameInput);
    await user.type(nameInput, 'Đi lại');
    await user.click(screen.getByRole('button', { name: 'Tạo danh mục' }));
    expect(screen.getByRole('button', { name: 'Đang lưu...' })).toBeDisabled();
    expect(createCategory).toHaveBeenCalledTimes(1);

    await act(async () => finishCreate({ ...category, id: 99, name: 'Đi lại' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('opens an edit form populated from the selected card', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole('heading', { name: 'Ăn uống' });
    await user.click(screen.getByRole('button', { name: 'Sửa' }));
    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Chỉnh sửa danh mục' })).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Tên hiển thị')).toHaveValue('Ăn uống');
    expect(within(dialog).getByRole('button', { name: 'Ăn uống' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('confirms hide and restores hidden categories', async () => {
    const user = userEvent.setup();
    const firstRender = renderPage();
    await screen.findByRole('heading', { name: 'Ăn uống' });
    await user.click(screen.getByRole('button', { name: 'Ẩn' }));
    
    expect(screen.getByText('Ẩn danh mục?')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Ẩn danh mục' }));
    await waitFor(() => expect(hideCategory).toHaveBeenCalledWith(1));
    firstRender.unmount();

    getCategories.mockResolvedValue(response([{ ...category, is_active: false }]));
    renderPage();
    await user.click(screen.getByText('Đang sử dụng'));
    await user.click(screen.getByText('Đã ẩn'));
    await screen.findByRole('heading', { name: 'Ăn uống' });
    await user.click(screen.getByRole('button', { name: 'Khôi phục' }));
    await waitFor(() => expect(restoreCategory).toHaveBeenCalledWith(1));
  });
});

describe('Category components', () => {
  it('renders a card with statistics and the restore action when hidden', () => {
    const onRestore = vi.fn();
    render(
      <CategoryCard
        category={{ ...category, is_active: false }}
        onEdit={vi.fn()}
        onHide={vi.fn()}
        onRestore={onRestore}
        busy={false}
      />,
    );

    expect(screen.getByRole('heading', { name: 'Ăn uống' })).toBeInTheDocument();
    expect(screen.getByText(/3 giao dịch/)).toBeInTheDocument();
    expect(screen.getByText(/25.00% tổng chi/)).toBeInTheDocument();
    expect(screen.getByText(/250\.000/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Khôi phục' }));
    expect(onRestore).toHaveBeenCalledWith(expect.objectContaining({ id: 1 }));
  });

  it('formats large decimal amounts without IEEE-754 precision loss', () => {
    render(
      <CategoryCard
        category={{ ...category, total_amount: '10000000000000000.01' }}
        onEdit={vi.fn()}
        onHide={vi.fn()}
        onRestore={vi.fn()}
        busy={false}
      />,
    );
    expect(screen.getByText((_, element) => (
      element.tagName === 'STRONG'
      && element.textContent === '10.000.000.000.000.000,01\u00a0₫'
    ))).toBeInTheDocument();
  });

  it('changes only the icon when selecting a preset while editing', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <CategoryFormModal
        category={{ ...category, name: 'Cà phê', color: '#123456', type: 'expense' }}
        submitting={false}
        apiError=""
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'Đi lại' }));
    await user.click(screen.getByRole('button', { name: 'Lưu thay đổi' }));
    expect(onSubmit).toHaveBeenCalledWith({
      name: 'Cà phê',
      icon: 'transport',
      color: '#123456',
      type: 'expense',
    });
  });

  it('uses a safe icon path and displays a fallback after an asset error', () => {
    const { container } = render(<CategoryIcon icon="../../secret" color="#C87941" />);
    const image = container.querySelector('img');
    expect(image.getAttribute('src')).toMatch(/other\.png$/);
    fireEvent.error(image);
    expect(screen.getByText('✨')).toBeInTheDocument();
  });

  it('shows validation and prevents an empty category submission', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <CategoryFormModal
        category={null}
        submitting={false}
        apiError=""
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    );
    const nameInput = screen.getByLabelText('Tên hiển thị');
    await user.clear(nameInput);
    await user.click(screen.getByRole('button', { name: 'Tạo danh mục' }));
    expect(screen.getByText('Tên danh mục không được để trống.')).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('disables the form and displays API conflict while submitting', () => {
    render(
      <CategoryFormModal
        category={null}
        submitting
        apiError="Tên danh mục đã tồn tại."
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('Tên danh mục đã tồn tại');
    expect(screen.getByRole('button', { name: 'Đang lưu...' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Hủy' })).toBeDisabled();
  });
});
